package de.seemoo.sonar

import android.content.Context
import android.os.Bundle
import android.os.ConditionVariable
import android.text.Editable
import android.text.InputType
import android.util.Log
import androidx.fragment.app.Fragment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.ViewTreeObserver
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import androidx.core.text.set
import com.google.android.material.floatingactionbutton.FloatingActionButton
import java.util.*

class NetworkSetupFragment : Fragment() {
    private var cv: ConditionVariable? = null
    private var txt: EditText? = null
    private var psk: EditText? = null
    var fab: FloatingActionButton? = null

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        // Inflate the layout for this fragment
        return inflater.inflate(R.layout.fragment_network_setup, container, false)


    }

    fun setBlockvar_ssid(bv: ConditionVariable, ssid: String) {
        cv = bv
        txt?.setText(ssid.replace("\"",""))
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {

        txt = view.findViewById(R.id.SSID)
        fab = view.findViewById(R.id.wififab)
        psk = view.findViewById(R.id.PSK)

        // default psk
        val sharedPref = context?.getSharedPreferences(getString(R.string.preference_file_key) ,Context.MODE_PRIVATE)
        val pskStr = sharedPref?.getString("PSK", "12345678")
        Log.d("SONARNW", pskStr!!)
        psk?.setText(pskStr)

        fab!!.setOnClickListener {
            cv?.open()
        }

        txt?.setOnEditorActionListener { v, actionId, event ->
            if(actionId == EditorInfo.IME_ACTION_DONE){
                cv?.open()
                true
            } else {
                false
            }
        }
        psk?.setOnEditorActionListener { v, actionId, event ->
            if(actionId == EditorInfo.IME_ACTION_DONE){
                cv?.open()
                true
            } else {
                false
            }
        }

        fun View.focusAndShowKeyboard() {
            fun View.showTheKeyboardNow() {
                if (isFocused) {
                    post {
                        // We still post the call, just in case we are being notified of the windows focus
                        // but InputMethodManager didn't get properly setup yet.
                        val imm = context.getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
                        imm.showSoftInput(this, InputMethodManager.SHOW_IMPLICIT)
                    }
                }
            }

            requestFocus()
            if (hasWindowFocus()) {
                // No need to wait for the window to get focus.
                showTheKeyboardNow()
            } else {
                // We need to wait until the window gets focus.
                viewTreeObserver.addOnWindowFocusChangeListener(
                    object : ViewTreeObserver.OnWindowFocusChangeListener {
                        override fun onWindowFocusChanged(hasFocus: Boolean) {
                            // This notification will arrive just before the InputMethodManager gets set up.
                            if (hasFocus) {
                                this@focusAndShowKeyboard.showTheKeyboardNow()
                                // It’s very important to remove this listener once we are done.
                                viewTreeObserver.removeOnWindowFocusChangeListener(this)
                            }
                        }
                    })
            }
        }

        psk?.focusAndShowKeyboard()

        super.onViewCreated(view, savedInstanceState)
    }

    fun getResult(): List<String> {
        return listOf(txt?.text.toString(), psk?.text.toString())
    }

}