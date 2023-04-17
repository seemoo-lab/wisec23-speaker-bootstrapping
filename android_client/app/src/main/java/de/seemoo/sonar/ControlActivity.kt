package de.seemoo.sonar

import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Base64
import android.util.Log
import android.view.Menu
import android.view.MenuInflater
import android.view.MenuItem
import android.widget.Button
import android.widget.Toast
import androidx.core.view.get
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.room.Room
import com.google.android.material.snackbar.Snackbar
import com.goterl.lazysodium.LazySodiumAndroid
import com.goterl.lazysodium.SodiumAndroid
import com.goterl.lazysodium.interfaces.AEAD
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.io.InputStream
import java.io.OutputStream
import java.lang.Exception
import java.net.Inet4Address
import java.net.Inet6Address
import java.net.Socket
import java.util.*

class ControlActivity : AppCompatActivity() {

    val TAG = "Control"

    var sock: Socket? = null
    var tcp_out: OutputStream? = null
    var tcp_in: InputStream? = null
    var uuid_spk: String? = null
    var uuid: String? = null
    var key: ByteArray? = null
    var new_dev_sbar: Snackbar? = null

    private fun writeOutputStream(ostr : OutputStream, msg : String) {
        val msgWEnd = msg + '\r'
        ostr.write(msgWEnd.toByteArray())
        ostr.flush()
    }

    private fun read_input_stream(instr : InputStream): String {
        var tmp_str = ""
        while(true) {
            val b = instr.read().toChar()
            if(b == '\r') {
                if (tmp_str == "NOK")
                    throw Exception("Protocol Error!")
                return tmp_str
            }else {
                tmp_str += b
            }
        }
    }

    private fun sendCommand(cmd: String, arg: String) {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val json = JSONObject()
                json.put("from", uuid)
                json.put("to", uuid_spk)
                json.put("cmd", cmd)
                json.put("arg", arg)

                val settings = json.toString()
                writeOutputStream(tcp_out!!, encryptString(settings))
            }catch (e: Exception) {
                //make sure we are in foreground
                if(this@ControlActivity.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
                    runOnUiThread {
                        Log.e(TAG, e.toString())
                        val toast = Toast.makeText(
                            applicationContext,
                            "Connection closed!",
                            Toast.LENGTH_SHORT
                        )
                        toast.show()
                    }
                }
                finish()
            }

        }
    }

    private fun encryptString(data: String) : String {
        val lz = LazySodiumAndroid(SodiumAndroid())
        val sb = lz as AEAD.Lazy

        // XCHACHA recommended by sodium docu, so using it here
        val nonce: ByteArray = lz.nonce(AEAD.XCHACHA20POLY1305_IETF_NPUBBYTES)
        val ciphertext = sb.encrypt(data, uuid+uuid_spk, nonce, com.goterl.lazysodium.utils.Key.fromBytes(key), AEAD.Method.XCHACHA20_POLY1305_IETF)

        // as the python bindings do not include sodiums bin2hex function, we reencode to base64
        val cipher_plain = lz.sodiumHex2Bin(ciphertext)
        val cipher_b64 = Base64.encodeToString(cipher_plain, Base64.NO_WRAP)

        //place encrypted block into JSON
        val json = JSONObject()
        json.put("ciphertext", cipher_b64)
        json.put("nonce", Base64.encodeToString(nonce, Base64.NO_WRAP))
        json.put("from", uuid)
        json.put("to", uuid_spk)
        json.put("pairing_req", false)

        return json.toString()
    }

    private val lz = LazySodiumAndroid(SodiumAndroid())
    private val sb = lz as AEAD.Lazy
    private fun decryptString(data: String) : String {

        val json = JSONObject(data)

        val cipher = Base64.decode(json.getString("ciphertext"), 0)
        val nonce = Base64.decode(json.getString("nonce"), 0)
        val from = json.getString("from")
        val to = json.getString("to")

        Log.d(TAG, from+to)

        val plaintext = sb.decrypt(lz.sodiumBin2Hex(cipher),
            from+to, nonce, com.goterl.lazysodium.utils.Key.fromBytes(key),  AEAD.Method.XCHACHA20_POLY1305_IETF)



        Log.d(TAG, plaintext)
        return plaintext
    }

    var menuOpt: Menu? = null
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        val inflater: MenuInflater = menuInflater
        inflater.inflate(R.menu.controlmenu, menu)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        menuOpt = menu
        return true

    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        // Handle item selection
        return when (item.itemId) {
            R.id.pm_always -> {
                Log.d(TAG, "pair always")
                sendCommand("PMOD", "always")
                item.isChecked = true
                true
            }
            R.id.pm_explicit -> {
                Log.d(TAG, "pair explicit")
                sendCommand("PMOD", "explicit")
                item.isChecked = true
                true
            }
            R.id.pm_timer -> {
                Log.d(TAG, "pair timer")
                sendCommand("PMOD", "timer")
                item.isChecked = true
                true
            }
            R.id.pair_now -> {
                Log.d(TAG, "pair now")
                sendCommand("PAIRALLOW", "")
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }


    val timer = Timer()
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_control)



        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        uuid = this.getSharedPreferences(getString(R.string.preference_file_key) , Context.MODE_PRIVATE).getString(getString(R.string.uuid), "")

        new_dev_sbar = Snackbar.make(findViewById<Button>(R.id.play), "A device requests pairing", Snackbar.LENGTH_INDEFINITE)
            .setAction("Allow") {
                sendCommand("PAIRALLOW", "")
            }

        lifecycleScope.launch(Dispatchers.IO) {

            try {
                val conMan = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
                conMan.bindProcessToNetwork(conMan.activeNetwork)

                val ip = intent.getStringExtra("ip")?.replace("/", "")
                uuid_spk = intent.getStringExtra("uuid")
                if(ip!!.length <= 15) {
                    sock = Socket(Inet4Address.getByName(ip), 6969)
                    Log.d(TAG, "v4")
                }
                else {
                    sock = Socket(Inet6Address.getByName(ip), 6969)
                    Log.d(TAG, "v6")
                }
                tcp_out = sock!!.getOutputStream()
                tcp_in = sock!!.getInputStream()
            }catch (e: Exception) {
                Log.d(TAG, e.toString())
                runOnUiThread {
                    val text = "Unable to connect!"
                    val duration = Toast.LENGTH_SHORT
                    val toast = Toast.makeText(applicationContext, text, duration)
                    toast.show()
                }
                finish()
            }

            val db = Room.databaseBuilder(
                applicationContext,
                UserStore.UserDB::class.java, "userstore"
            ).enableMultiInstanceInvalidation().build()

            key = Base64.decode(db.userDao().getUser(uuid_spk!!).key_enc, 0)

        }

        findViewById<Button>(R.id.play).setOnClickListener {
            lifecycleScope.launch(Dispatchers.IO) {
                sendCommand("PLAY", "")
            }
        }
        findViewById<Button>(R.id.pause).setOnClickListener {
            lifecycleScope.launch(Dispatchers.IO) {
                sendCommand("STOP", "")
            }
        }
        findViewById<Button>(R.id.volp).setOnClickListener {
            lifecycleScope.launch(Dispatchers.IO) {
                sendCommand("MORE", "")
            }
        }
        findViewById<Button>(R.id.voln).setOnClickListener {
            lifecycleScope.launch(Dispatchers.IO) {
                sendCommand("LESS", "")
            }
        }

        val mainHandler = Handler(Looper.getMainLooper())

        //run updateState every second
        /*mainHandler.postDelayed(object : Runnable {
            override fun run() {
                updateState()
                mainHandler.postDelayed(this, 1000)
            }
        }, 1000)*/
        timer.scheduleAtFixedRate(
            object : TimerTask() {

                override fun run() {
                    updateState()
                }

            },1000, 1000
        )

    }

    override fun onDestroy() {
        timer.cancel()
        super.onDestroy()
    }

    fun updateState() {
        lifecycleScope.launch(Dispatchers.IO) {
            sendCommand("INFO", "")
            try {
                val message = read_input_stream(tcp_in!!)
                val info = decryptString(message)
                val json_state = JSONObject(info)
                val waiting = json_state.getBoolean("waiting")
                val pair = json_state.getString("pair")
                val time_rem = json_state.getInt("timer")

                System.gc()

                runOnUiThread {
                    when (pair) {
                        "always" -> {
                            menuOpt?.findItem(R.id.pm_always)?.isChecked = true
                            menuOpt?.findItem(R.id.pair_now)?.title = "Pairing already allowed"
                            menuOpt?.findItem(R.id.pair_now)?.isEnabled = false
                        }
                        "timer" -> {
                            menuOpt?.findItem(R.id.pm_timer)?.isChecked = true
                            menuOpt?.findItem(R.id.pair_now)?.isEnabled = time_rem <= 0
                            if(time_rem > 0)
                                menuOpt?.findItem(R.id.pair_now)?.title = "Pairing already allowed"
                            else
                                menuOpt?.findItem(R.id.pair_now)?.title = "Allow pairing for five minutes"

                        }

                        "explicit" -> {
                            menuOpt?.findItem(R.id.pm_explicit)?.isChecked = true
                            if(waiting) {
                                menuOpt?.findItem(R.id.pair_now)?.title = "Allow pairing"
                                menuOpt?.findItem(R.id.pair_now)?.isEnabled = true
                                new_dev_sbar?.show()
                            }
                            else {
                                menuOpt?.findItem(R.id.pair_now)?.title = "No device waiting"
                                menuOpt?.findItem(R.id.pair_now)?.isEnabled = false
                                new_dev_sbar?.dismiss()
                            }


                        }
                    }
                }


            }catch (x: Exception) {

                Log.d(TAG, x.toString())
            }

        }
    }

    override fun onBackPressed() {
        sock?.close()
        this.finish()
    }
    override fun onSupportNavigateUp(): Boolean {
        sock?.close()
        this.finish()
        return true
    }

}