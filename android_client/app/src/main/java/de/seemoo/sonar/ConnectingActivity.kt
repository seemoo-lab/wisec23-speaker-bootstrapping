package de.seemoo.sonar

import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import android.net.wifi.WifiNetworkSpecifier
import android.os.Bundle
import android.os.ConditionVariable
import android.os.SystemClock
import android.provider.Settings
import android.util.Base64
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.lifecycle.lifecycleScope
import androidx.navigation.findNavController
import androidx.navigation.fragment.NavHostFragment
import androidx.room.Room
import com.google.android.material.snackbar.Snackbar
import com.goterl.lazysodium.LazySodiumAndroid
import com.goterl.lazysodium.SodiumAndroid
import com.goterl.lazysodium.interfaces.*
import com.goterl.lazysodium.interfaces.Random
import com.goterl.lazysodium.utils.Key
import de.seemoo.sonar.databinding.ActivityConnectingBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.json.JSONObject
import org.quietmodem.Quiet.FrameReceiver
import org.quietmodem.Quiet.FrameReceiverConfig
import java.io.*
import java.net.Inet4Address
import java.net.Socket
import java.util.*
import kotlin.concurrent.timerTask
import kotlin.random.Random.Default.nextInt

val pairPort = 17099
val defaultIP = "10.42.0.1"

class ConnectingActivity : AppCompatActivity() {

    private lateinit var binding: ActivityConnectingBinding
    private var TAG = "sonar"

    private val pass_len = 8
    private val suffix_len = 4
    private val nw_prefix = "SEEMOO_SPEAKER_"


    //Function to read from an input stream
    //reads up to \r and returns read string
    //if string is NOK, raises exception
    private fun readInputStream(instr : InputStream): String {
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

    //write string to stream
    //add trailing \r for end detection
    private fun writeOutputStream(ostr : OutputStream, msg : String) {
        val msgWEnd = msg + '\r'
        ostr.write(msgWEnd.toByteArray())
    }

    //helper function to create encrypted settings packet
    private fun networkSettings(wname: String, pass: String, key: Key, name: String): String {
        val json = JSONObject()
        json.put("name", wname)
        json.put("key", pass)
        json.put("host", name)

        val settings = json.toString()
        return encryptString(settings, key, "")
    }

    //encrypt string with XCHACHA (recommended by sodium docu) and return as JSON
    fun encryptString(data: String, key: Key, add_data: String) : String {
        val lz = LazySodiumAndroid(SodiumAndroid())
        val sb = lz as AEAD.Lazy

        //create random nonce
        val nonce: ByteArray = lz.nonce(AEAD.XCHACHA20POLY1305_IETF_NPUBBYTES)
        //encrypt
        val ciphertext = sb.encrypt(data, add_data, nonce, key, AEAD.Method.XCHACHA20_POLY1305_IETF)
        // as the python bindings do not include sodiums bin2hex function, we reencode to base64
        val cipherPlain = lz.sodiumHex2Bin(ciphertext)
        val cipherB64 = Base64.encodeToString(cipherPlain, Base64.NO_WRAP)

        //place encrypted block into JSON
        val json = JSONObject()
        json.put("ciphertext", cipherB64)
        json.put("nonce", Base64.encodeToString(nonce, Base64.NO_WRAP))
        json.put("additional", add_data)

        return json.toString()
    }

    //create integer from byte array
    //needed for word selection
    private fun littleEndianConversion(bytes: ByteArray): UInt {
        var result = 0U
        for (i in 0..3) {
            result = result or ( (bytes[i].toUInt() and 0xffU) shl (8 * i) )
        }
        return result
    }

    //get random field from array
    private fun getRandom(array: ArrayList<String>): String {
        val rnd: Int = nextInt(array.size)
        return array[rnd]
    }


    //hold tcp connection here
    private var tcpSock: Socket? = null
    private var tcpOut: OutputStream? = null
    private var tcpIn: InputStream? = null

    //close sock when activity is closed
    override fun onDestroy() {
        closeSock()
        super.onDestroy()
    }

    //main pairing function, returns uuid, name and keys
    private fun connect() : ArrayList<String> {

        //get own UUID
        val sharedPref = this.getSharedPreferences(getString(R.string.preference_file_key) ,Context.MODE_PRIVATE)
        val clientUuid = UUID.fromString(sharedPref.getString(getString(R.string.uuid), ""))
        Log.d(TAG, "UUID: $clientUuid")

        //****
        //evaluate passed intent data
        //mainly if this is initial or follow-up pairing
        val initial = intent.getBooleanExtra("ini", false)
        Log.d(TAG, "init: $initial")
        val navCon = this.findNavController(R.id.nav_host_fragment_content_connecting)


        //request pairing
        if (!initial) {
                try {
                    val ip = intent.getStringExtra("ip")?.replace("/", "")
                    val uuidSpk = intent.getStringExtra("uuid")
                    val uuid = UUID.fromString(sharedPref.getString(getString(R.string.uuid), ""))

                    Log.d(TAG, "connect $ip")
                    tcpSock = Socket(Inet4Address.getByName(ip), pairPort) //connect
                    Log.d(TAG, "connected")

                    tcpOut = tcpSock?.getOutputStream()
                    tcpIn = tcpSock?.getInputStream()

                    //get reply
                    val repl = readInputStream(tcpIn!!)

                    //evaluate if pairing was granted
                    if (repl == "KO") {
                        runOnUiThread {
                            val toast = Toast.makeText(
                                applicationContext,
                                "Pairing is not allowed!",
                                Toast.LENGTH_SHORT
                            )
                            toast.show()
                        }
                        finish()
                    }
                    if (repl == "EX") {
                        this@ConnectingActivity.runOnUiThread {
                            navCon.navigate(R.id.action_FirstFragment_to_requestFragment)
                        }
                        readInputStream(tcpIn!!)
                        this@ConnectingActivity.runOnUiThread {
                            navCon.navigate(R.id.action_requestFragment_to_FirstFragment)
                        }
                    }


                } catch (e: java.lang.Exception) {
                    Log.d(TAG, e.toString())
                    runOnUiThread {
                        val toast = Toast.makeText(
                            applicationContext,
                            "Unable to connect!",
                            Toast.LENGTH_SHORT
                        )
                        toast.show()
                    }
                    closeSock()
                    finish()
                }
        }


        //****
        //generate ecdh key
        val lz = LazySodiumAndroid(SodiumAndroid())
        val sb = lz as DiffieHellman.Lazy
        val clientPrivateKey = Key.fromBytes(lz.randomBytesBuf(DiffieHellman.SCALARMULT_CURVE25519_BYTES))
        val clientDhComponent = Base64.encodeToString(sb.cryptoScalarMultBase(clientPrivateKey).asBytes, 0)

        //set up libquiet reception
        val receiverConfig = FrameReceiverConfig(
            this,
            "custom" //our custom ultrasonic profile
        )

        val receiver = FrameReceiver(receiverConfig)

        //fully block while receiving pairing code
        //no timeout here
        receiver.setBlocking(0, 0)

        //receive pairing code
        val acousticCodeBuffer = ByteArray(40) //buffer for reception
        var recLen: Long = 0

        var snackbarTimer = Timer()
        val helperSbar = Snackbar.make(this.findViewById(R.id.mainLayoutCA), "You seem to have issues in scanning the pairing code. Point the bottom of your phone towards the speaker.", Snackbar.LENGTH_INDEFINITE)

        try {
            Log.d(TAG, "receiving...")
            snackbarTimer.schedule(timerTask {
                runOnUiThread { helperSbar.show() }
            }, 20000)
            recLen = receiver.receive(acousticCodeBuffer)
        } catch (e: IOException) {
            Log.d(TAG, "Quiet timeout")
        }

        runOnUiThread { helperSbar.dismiss() }
        snackbarTimer.cancel()

        //segment pairing code into contained parts
        val acousticString = String(acousticCodeBuffer)
        Log.d(TAG, "Received $recLen : $acousticString")

        val pairTypeAcoustic = acousticString[0]
        val hashAcousticB64 = acousticString.substring(1, (recLen-pass_len-suffix_len).toInt())
        val networkSuffix = acousticString.substring((recLen-pass_len-suffix_len).toInt(), (recLen-pass_len).toInt())
        val networkPass = acousticString.substring((recLen-pass_len).toInt(), recLen.toInt())
        val pairingSecret = networkSuffix + networkPass

        Log.d(TAG, "Received segmented type $pairTypeAcoustic hash $hashAcousticB64 suffix $networkSuffix pass $networkPass")

        //Hold wifi information during initial pairing
        //necessary as those fields will be used for disconnection in another block
        val connectManager = this.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        var networkCallback: ConnectivityManager.NetworkCallback? = null
        var currentNwId = 0
        var currentSsid = ""
        val wifiManager = this.getSystemService(Context.WIFI_SERVICE) as WifiManager

        //for initial pairing connect to temp network
        if(initial) {
            //connect to spun-up wifi network
            //build network description
            val networkSpecBuilder = WifiNetworkSpecifier.Builder()
            networkSpecBuilder.setSsid(nw_prefix + networkSuffix)
            networkSpecBuilder.setWpa2Passphrase(networkPass)
            val networkSpec = networkSpecBuilder.build()
            //build connection request
            val networkRequestBuilder = NetworkRequest.Builder()
            networkRequestBuilder.addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            networkRequestBuilder.setNetworkSpecifier(networkSpec)
            val networkRequest = networkRequestBuilder.build()
            //save info about currently connected network for later use
            currentSsid = wifiManager.connectionInfo.ssid
            currentNwId = wifiManager.connectionInfo.networkId
            //semaphore for waiting
            val waitForNetwork = ConditionVariable(false)
            //buffer to hold connection
            var nwConnection: Network? = null

            //callback object for successful/unsuccessful connection
            networkCallback = object : ConnectivityManager.NetworkCallback() {
                //if successful, open semaphore and store network object
                override fun onAvailable(network: Network) {
                    Log.d(TAG, "Network avail")
                    nwConnection = network
                    waitForNetwork.open()
                    super.onAvailable(network)
                }
                //if unavailable, throw exception and exit
                override fun onUnavailable() {
                    Log.d(TAG, "Network unavail")
                    super.onUnavailable()
                    this@ConnectingActivity.closeSock()
                    this@ConnectingActivity.finish()
                }

            }

            //connect to network
            connectManager.requestNetwork(networkRequest, networkCallback)
            waitForNetwork.block()
            connectManager.bindProcessToNetwork(nwConnection)
        }

        //set up tcp socket for comms
        if(initial)
            tcpSock = Socket(Inet4Address.getByName(defaultIP), pairPort) //use default IP to connect if initial

            //get streams for tcp socket
            tcpOut = tcpSock!!.getOutputStream()
            tcpIn = tcpSock!!.getInputStream()


        //get devices nickname
        val devName = Settings.Secure.getString(contentResolver, "bluetooth_name");

        //send UUID, DH key and name
        writeOutputStream(tcpOut!!, clientUuid.toString())
        writeOutputStream(tcpOut!!, clientDhComponent)
        writeOutputStream(tcpOut!!, devName)


        //receive components from server
        val uuidServerStr = readInputStream(tcpIn!!)
        val dhServerB64 = readInputStream(tcpIn!!)
        val uuidServer = UUID.fromString(uuidServerStr)
        Log.d(TAG,"UUID_Server: $uuidServer")

        //check hash from acoustic code against data from server
        val gh = lz as GenericHash.Native
        val hash: ByteArray = lz.randomBytesBuf(16)
        val hashData = (dhServerB64 + uuidServer).toByteArray()
        gh.cryptoGenericHash(hash, hash.size, hashData, hashData.size.toLong())
        Log.d(TAG, "Hash: ${Base64.encodeToString(hash, 0)}")
        //if assertion fails, exit
        if(!hash.contentEquals(Base64.decode(hashAcousticB64, 0))) {
            throw IOException("Acoustic hash does not match")
        }

        //exchange keys
        val dhServer = Key.fromBytes(Base64.decode(dhServerB64, 0)) //wrap data from srv into key object
        val secret = sb.cryptoScalarMult(clientPrivateKey, dhServer) //defer secret

        //defer keys
        val kdf = lz as KeyDerivation.Lazy
        val keyEncrypt = kdf.cryptoKdfDeriveFromKey(32, 0, "encrypt ", secret)
        val keySign = kdf.cryptoKdfDeriveFromKey(32, 0, "sign    ", secret)
        val keyVerify =kdf.cryptoKdfDeriveFromKey(32, 0, "verify  ", secret)

        //Calculate MAC over client components
        //proves to server that we deferred the same key
        var textToMac: String? = null
        textToMac = if (initial)
            clientUuid.toString() + clientDhComponent + devName
        else
            clientUuid.toString() + clientDhComponent + devName + pairingSecret //if followup pairing, also include secret from acoustic msg as no wifi auth was necessary
            //authenticates client
        Log.d(TAG, "MAC text: $textToMac")

        //compute MAC using signing key
        val auth = lz as Auth.Lazy
        val mac = auth.cryptoAuth(textToMac, keySign)
        val macB64 = Base64.encodeToString(lz.sodiumHex2Bin(mac), Base64.NO_WRAP)
        Log.d(TAG, "MAC: $macB64")
        writeOutputStream(tcpOut!!, macB64) //send


        this@ConnectingActivity.runOnUiThread {
            navCon.navigate(R.id.action_FirstFragment_to_confirmFragment)
        }

        //wait for user confirmation at speaker
        readInputStream(tcpIn!!) //server may abort here if mac is broken or user disproves at spk

        this@ConnectingActivity.runOnUiThread {
            navCon.navigate(R.id.action_confirmFragment_to_wordselect)
        }

        //read word file
        val stream = resources.openRawResource(R.raw.wordlist)
        val reader = BufferedReader(InputStreamReader(stream))
        val words = ArrayList<String>()
        while (reader.ready()) {
            val line = reader.readLine()
            words.add(line)
        }


        //pick word using verify key
        val rand = lz as Random
        val chosenIndex = rand.randomBytesDeterministic(Int.SIZE_BYTES, keyVerify.asBytes)
        val chosenInt = littleEndianConversion(chosenIndex) % words.size.toUInt()
        val chosenWord = words[chosenInt.toInt()]
        Log.d(TAG, "chosen: $chosenWord")
        //mutex to wait for word selection
        val waitForWordSelect = ConditionVariable(false)

        this@ConnectingActivity.runOnUiThread {
            val navHost = this@ConnectingActivity.supportFragmentManager.primaryNavigationFragment as NavHostFragment
            navHost.let { navFragment ->
                navFragment.childFragmentManager.primaryNavigationFragment?.let {fragment->
                    //show selected word and four additional ones on screen
                    (fragment as WordSelectFragment).setTexts(ArrayList(listOf(chosenWord, getRandom(words), getRandom(words), getRandom(words), getRandom(words))), waitForWordSelect)
                }
            }

        }
        //wait till result available
        waitForWordSelect.block()

        //get result from word selection
        var result = false
        val waitRes = ConditionVariable(false)
        this@ConnectingActivity.runOnUiThread {
            val navHost = this@ConnectingActivity.supportFragmentManager.primaryNavigationFragment as NavHostFragment
            navHost.let { navFragment ->
                navFragment.childFragmentManager.primaryNavigationFragment?.let {fragment->
                    result = (fragment as WordSelectFragment).getResult()
                    waitRes.open()
                }
            }
        }
        waitRes.block()
        //if wrong word picked, die
        if(result) {
            writeOutputStream(tcpOut!!, "OK")
            Log.d(TAG, "Write OK")
        }else {
            writeOutputStream(tcpOut!!, "NOK")
            Log.d(TAG, "Write NOK")
        }

        var spkName = "" //buffer for speaker name


        //let User name
        if(initial) {
            this@ConnectingActivity.runOnUiThread {
                navCon.navigate(R.id.action_wordselect_to_namingFragment)
            }
            SystemClock.sleep(10) //necessary as the next block otherwise gets the previous fragment
            val waitNaming = ConditionVariable(false)
            this@ConnectingActivity.runOnUiThread {
                val navHost =
                    this@ConnectingActivity.supportFragmentManager.primaryNavigationFragment as NavHostFragment
                navHost.let { navFragment ->
                    navFragment.childFragmentManager.primaryNavigationFragment?.let { fragment ->
                        (fragment as NamingFragment).setBlockvar(waitNaming)
                    }
                }
            }
            waitNaming.block()
            //read name
            val waitGetName = ConditionVariable(false)
            this@ConnectingActivity.runOnUiThread {
                val navHost =
                    this@ConnectingActivity.supportFragmentManager.primaryNavigationFragment as NavHostFragment
                navHost.let { navFragment ->
                    navFragment.childFragmentManager.primaryNavigationFragment?.let { fragment ->
                        spkName = (fragment as NamingFragment).getResult()
                    }
                    waitGetName.open()
                }
            }
            waitGetName.block()


            //Let the user setup Networking
            this@ConnectingActivity.runOnUiThread {
                navCon.navigate(R.id.action_namingFragment_to_networkSetupFragment)
            }
            SystemClock.sleep(100) //necessary as the next block otherwise gets the previous fragment
            val waitNw = ConditionVariable(false)
            this@ConnectingActivity.runOnUiThread {
                val navHost =
                    this@ConnectingActivity.supportFragmentManager.primaryNavigationFragment as NavHostFragment
                navHost.let { navFragment ->
                    navFragment.childFragmentManager.primaryNavigationFragment?.let { fragment ->
                        (fragment as NetworkSetupFragment).setBlockvar_ssid(waitNw, currentSsid)
                    }
                }
            }
            waitNw.block()

            val waitGetWifi = ConditionVariable(false)
            var wifiSetting: List<String>? = null

            this@ConnectingActivity.runOnUiThread {
                val navHost =
                    this@ConnectingActivity.supportFragmentManager.primaryNavigationFragment as NavHostFragment
                navHost.let { navFragment ->
                    navFragment.childFragmentManager.primaryNavigationFragment?.let { fragment ->
                        wifiSetting = (fragment as NetworkSetupFragment).getResult()
                    }
                    waitGetWifi.open()
                }
            }
            waitGetWifi.block()
            //send encrypted package with network configuration
            val ciphertext =
                networkSettings(wifiSetting?.get(0) ?: "", wifiSetting?.get(1) ?: "", keyEncrypt, spkName)
            Log.d(TAG, "ciphertext: $ciphertext")
            writeOutputStream(tcpOut!!, ciphertext)

            this@ConnectingActivity.runOnUiThread {
                navCon.navigate(R.id.action_networkSetupFragment_to_searchingFragment)
            }

            SystemClock.sleep(1000) //slow pause to mitigate closing socket too early
        }

        closeSock()

        var name: String? = null

        if(initial) {
            //disconnect from temporary network
            connectManager.unregisterNetworkCallback(networkCallback!!)
            wifiManager.disconnect();
            wifiManager.enableNetwork(currentNwId, true);
            wifiManager.reconnect();
            //start browsing for wifi networks and zeroconf
            val nsdManager = getSystemService(NSD_SERVICE) as NsdManager
            val waitForDiscovery = ConditionVariable(false)
            //callback obj for service discovery
            val discoveryListener = object : NsdManager.DiscoveryListener {

                override fun onStartDiscoveryFailed(p0: String?, p1: Int) {
                    Log.d(TAG, "Service discovery failed to start " + p0 + p1.toString())
                    throw Exception("Discovery fail")
                }

                override fun onStopDiscoveryFailed(p0: String?, p1: Int) {

                }

                // Called as soon as service discovery begins.
                override fun onDiscoveryStarted(regType: String) {
                    Log.d(TAG, "Service discovery started")
                }

                override fun onServiceFound(service: NsdServiceInfo) {
                    if (uuidServer.toString() == service.serviceName) { //check if correct speaker
                        name = spkName
                        waitForDiscovery.open() //notify
                        Log.d(TAG, "found in NW")
                    }
                }

                override fun onServiceLost(service: NsdServiceInfo) {
                    // When the network service is no longer available.
                    // Internal bookkeeping code goes here.
                    Log.e(TAG, "service lost: $service")
                }

                override fun onDiscoveryStopped(serviceType: String) {
                    Log.i(TAG, "Discovery stopped: $serviceType")
                }
            }

            //set up service browser
            nsdManager.discoverServices(
                "_SEEMOOSPEAKER._tcp",
                NsdManager.PROTOCOL_DNS_SD,
                discoveryListener
            )

            Log.d(TAG, "wait for discovery")
            waitForDiscovery.block() //wait for service browser
            Log.d(TAG, "discovered")
        }

        //pull speaker name from intent if followup pairing
        if(!initial) {
            name = intent.getStringExtra("name")
        }

        //base64 encode keys
        val encB64 = Base64.encodeToString(keyEncrypt.asBytes, Base64.NO_WRAP)
        val sigB64 = Base64.encodeToString(keySign.asBytes, Base64.NO_WRAP)
        val verB64 = Base64.encodeToString(keyVerify.asBytes, Base64.NO_WRAP)
        Log.d(TAG, "keys b64ified")
        return arrayListOf(uuidServerStr, encB64, sigB64, verB64, name!!) //return parameters for DB
    }

    override fun onCreate(savedInstanceState: Bundle?) {



        //set layout up
        WindowCompat.setDecorFitsSystemWindows(window, false)
        super.onCreate(savedInstanceState)
        binding = ActivityConnectingBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        //start real pairing
        lifecycleScope.launch(Dispatchers.IO) {
            //real connecting procedure
            try {
                //connect to database
                val db = Room.databaseBuilder(
                    applicationContext,
                    UserStore.UserDB::class.java, "userstore"
                ).enableMultiInstanceInvalidation().build()
                val result = connect() //run pairing
                Log.d(TAG, "Connection done")

                //save new user
                db.userDao().insert(result[0], result[1], result[2], result[3], result[4])
                finish()
            }catch (e : Exception) {
                //inform user if error occurs
                Log.e(TAG, e.toString())
                runOnUiThread {
                    val toast = Toast.makeText(
                        applicationContext,
                        "Error during pairing!",
                        Toast.LENGTH_SHORT
                    )
                    toast.show()
                }
                //teardown
                closeSock()
                finish()
            }


        }

    }

    private fun closeSock() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                tcpOut?.let { writeOutputStream(tcpOut!!, "NOK") }
            }catch (e : Exception) {}
            SystemClock.sleep(200) //slow pause to mitigate closing socket too early
            tcpOut?.flush()
            tcpOut?.close()
            tcpIn?.close()
            tcpSock?.close()
            tcpOut = null
            tcpIn = null
            tcpSock = null
        }
    }

    //Make sure that we return to the same instance of the previously created
    //main activity to save loading time
    override fun onBackPressed() {
        closeSock()
        this.finish()
    }
    override fun onSupportNavigateUp(): Boolean {
        closeSock()
        this.finish()
        return true
    }
}
