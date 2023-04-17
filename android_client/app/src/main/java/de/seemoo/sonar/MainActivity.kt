package de.seemoo.sonar

import android.Manifest
import android.content.*
import android.content.pm.PackageManager
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import android.os.Bundle
import android.os.ConditionVariable
import android.util.Log
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.navigation.ui.AppBarConfiguration
import androidx.recyclerview.widget.DefaultItemAnimator
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.room.Room
import com.google.android.material.snackbar.Snackbar
import de.seemoo.sonar.databinding.ActivityMainBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.*


class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    val TAG = "Phasar"


    private var foundList = ArrayList<Speaker>()
    private var nsdManager: NsdManager? = null
    private var wifiManager: WifiManager? = null
    private var new_dev_sbar: Snackbar? = null
    private var sb_shown = false





    //****
    //Deal with zeroconf
    // Instantiate a new DiscoveryListener

    data class Service(val uuid: String, val IP: String, val name: String)
    val availableServices = ArrayList<Service>()

    class ResolveListener(private val availableServices: ArrayList<Service>, val updateList: () -> Unit) : NsdManager.ResolveListener {
        val TAG = "Sonar"


        override fun onResolveFailed(p0: NsdServiceInfo?, p1: Int) {
            Log.d(TAG, "resolve fail")
        }

        override fun onServiceResolved(service: NsdServiceInfo?) {

            Log.d(TAG, "Service discovery success $service")
            Log.d(TAG, "Service Type: ${service?.serviceType}")
            val uuid = service!!.attributes["uuid"]?.let { String(it) }
            val name = service.attributes["name"]?.let { String(it) }
            Log.d(TAG, "$uuid")
            Log.d(TAG, "$name")
            availableServices.add(Service(uuid!!, service.host.toString() ,name!!))

            updateList()
        }

    }

    private val discoveryListener = object : NsdManager.DiscoveryListener {

        override fun onStartDiscoveryFailed(p0: String?, p1: Int) {
            Log.d(TAG, "Service discovery failed to start " + p0 + p1.toString())
        }

        override fun onStopDiscoveryFailed(p0: String?, p1: Int) {

        }

        // Called as soon as service discovery begins.
        override fun onDiscoveryStarted(regType: String) {
            Log.d(TAG, "Service discovery started")
        }

        override fun onServiceFound(service: NsdServiceInfo) {
            val resolveListener = ResolveListener(availableServices) { updateList() }
            nsdManager?.resolveService(service, resolveListener)
        }

        override fun onServiceLost(service: NsdServiceInfo) {
            // When the network service is no longer available.
            // Internal bookkeeping code goes here.
            Log.d(TAG, "service lost: $service")
            for (i in availableServices) {
                if (i.uuid == service.serviceName) {
                    availableServices.remove(i)
                    break
                }
            }

            updateList()

        }

        override fun onDiscoveryStopped(serviceType: String) {
            Log.i(TAG, "Discovery stopped: $serviceType")
        }
    }

    //****
    //Deal with wifi scanning
    val wifiListener = object : BroadcastReceiver() {

        override fun onReceive(context: Context, intent: Intent) {
            val success = intent.getBooleanExtra(WifiManager.EXTRA_RESULTS_UPDATED, false)
            if (success) {
                handleWifiScan()
            }
            if (lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED))
                wifiManager?.startScan()
        }

        fun handleWifiScan() {
            val results = wifiManager?.scanResults
            var found = false
            results?.forEach {
                if(it.SSID.contains("SEEMOO_SPEAKER_"))
                    found = true
            }

            if(found && !sb_shown) {
                new_dev_sbar?.show()
                sb_shown = true
            }
            if(!found && sb_shown) {
                new_dev_sbar?.dismiss()
                sb_shown = false
            }
        }
    }

    private var m_adapter: ListViewAdapter? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        binding = ActivityMainBinding.inflate(layoutInflater)

        //****
        //get system services
        nsdManager = this.getSystemService(Context.NSD_SERVICE) as NsdManager
        wifiManager = this.getSystemService(Context.WIFI_SERVICE) as WifiManager

        //set action bar
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        //****
        //Create RecyclerView and set it up

        var recyclerView = binding.foundSpeakers
        // use this setting to improve performance if you know that changes
        // in content do not change the layout size of the RecyclerView
        recyclerView.setHasFixedSize(true)
        // use a linear layout manager

        // use a linear layout manager
        val layoutManager: RecyclerView.LayoutManager = LinearLayoutManager(this)
        recyclerView.layoutManager = layoutManager

        // specify an adapter (see also next example)
        m_adapter = ListViewAdapter(foundList, lifecycleScope, this)

        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.itemAnimator = DefaultItemAnimator()
        recyclerView.adapter = m_adapter


        //****
        //service discovery
        nsdManager?.discoverServices("_SEEMOOSPEAKER._tcp", NsdManager.PROTOCOL_DNS_SD, discoveryListener)


        //****
        //new device available snackbar
        new_dev_sbar = Snackbar.make(recyclerView, R.string.sb_new_dev_text, Snackbar.LENGTH_INDEFINITE)
            .setAction(R.string.sb_new_dev_action) {
                val switchActivityIntent = Intent(this, ConnectingActivity::class.java)
                switchActivityIntent.putExtra("ini", true)
                startActivity(switchActivityIntent)
            }


        //****
        //wifi network scanning
        val intentFilter = IntentFilter()
        intentFilter.addAction(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION)
        this.registerReceiver(wifiListener, intentFilter)

        val success = wifiManager?.startScan()
        if (!success!!) {
            // scan failure handling
            Log.d(TAG, "Wifi start fail!")
        }

        //****
        //initial value provider
        val sharedPref = this.getSharedPreferences(getString(R.string.preference_file_key) ,Context.MODE_PRIVATE)
        var uuid = sharedPref.getString(getString(R.string.uuid), "")

        if(uuid == "") {
            uuid = UUID.randomUUID().toString()
            with (sharedPref.edit()) {
                putString(getString(R.string.uuid), uuid)
                apply()
            }
            val switchActivityIntent = Intent(this, FirstUseActivity::class.java)
            startActivity(switchActivityIntent)
        }

        Log.d(TAG, "UUID: $uuid")

        val first = sharedPref.getBoolean("first", true)

        if(first) {
            with (sharedPref.edit()) {
                putBoolean("first", false)
                apply()
            }



        }

        /*val me = wifiManager!!.javaClass.methods
        for(i in me) {
            Log.d(TAG, i.toString())
        }*/

        //Runtime.getRuntime().exec("su");
        /*val handler = Handler(Looper.getMainLooper())
        handler.postDelayed({
            val m = wifiManager!!.javaClass.getMethod("getPrivilegedConfiguredNetworks")
            m.invoke(wifiManager)
        }, 10000)*/

    }

    val unique_speakers = HashMap<String, Speaker>()
    val guard_update = ConditionVariable(true)
    fun updateList() {
        guard_update.block()
        foundList.clear()
        unique_speakers.clear()

        val db = Room.databaseBuilder(
            applicationContext,
            UserStore.UserDB::class.java, "userstore"
        ).enableMultiInstanceInvalidation().build()

        val speakers = db.userDao().getAll()
        val avail_scratch = ArrayList(availableServices)

        for (u in speakers) {
            //find out if avail
            var avail = false
            var spk: Service? = null

            for (i in avail_scratch) {
                if(i.uuid == u.uid) {
                    spk = i
                    avail_scratch.remove(i)
                    avail = true
                }
            }

            if (avail) {
                unique_speakers[spk!!.uuid] = Speaker(spk.uuid, true, true, spk.IP, u.name)
            }else{
                unique_speakers[u.uid] = Speaker(u.uid, false, true, "-", u.name)
            }

        }

        for(i in avail_scratch) {
            unique_speakers[i.uuid] = Speaker(i.uuid, true, false, i.IP, i.name)
        }

        for(i in unique_speakers.toList())
            foundList.add(i.second)

        runOnUiThread {
            if(foundList.isEmpty()) {
                findViewById<TextView>(R.id.emptyText).visibility = View.VISIBLE
            }else{
                findViewById<TextView>(R.id.emptyText).visibility = View.INVISIBLE
            }
            m_adapter!!.notifyDataSetChanged()

            guard_update.open()
        }
    }

    override fun onResume() {

        // Reset network detection for assumption
        // of new device nearby
        sb_shown = false
        wifiManager?.startScan()

        //Ask for necessary permissions (otherwise some aspects may refuse to work)
        if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED)
            requestPermissions(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION, Manifest.permission.ACCESS_FINE_LOCATION), 87);

        if(checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED)
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 87);

        lifecycleScope.launch(Dispatchers.IO) {
            updateList()
        }
        super.onResume()
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        // Inflate the menu; this adds items to the action bar if it is present.
        menuInflater.inflate(R.menu.menu_main, menu)
        super.onCreateOptionsMenu(menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        // Handle action bar item clicks here. The action bar will
        // automatically handle clicks on the Home/Up button, so long
        // as you specify a parent activity in AndroidManifest.xml.

        val alert: AlertDialog.Builder = AlertDialog.Builder(this)

        alert.setTitle("Set default WiFi password")
        alert.setMessage("Change the default WiFi password here")

        val sharedPref = this.getSharedPreferences(getString(R.string.preference_file_key) ,Context.MODE_PRIVATE)
        val pskStr = sharedPref?.getString("PSK", "12345678")

        val input = EditText(this)
        input.setText(pskStr)
        alert.setView(input)

        alert.setPositiveButton("Ok"
        ) { _, _ ->
            val sharedPref = this.getSharedPreferences(getString(R.string.preference_file_key) ,Context.MODE_PRIVATE)
            sharedPref.edit().putString("PSK", input.text.toString()).apply()
        }

        alert.show()

        return true
    }

}