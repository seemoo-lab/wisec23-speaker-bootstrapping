package de.seemoo.sonar

import android.content.Context
import android.os.Bundle
import android.os.ConditionVariable
import android.text.InputType
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.ViewTreeObserver
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import androidx.core.content.ContextCompat.getSystemService
import androidx.fragment.app.Fragment
import com.google.android.material.floatingactionbutton.FloatingActionButton
import com.google.android.material.textfield.TextInputLayout


private const val ARG_PARAM1 = "param1"
private const val ARG_PARAM2 = "param2"

/**
 * A simple [Fragment] subclass.
 * Use the [NamingFragment.newInstance] factory method to
 * create an instance of this fragment.
 */
class NamingFragment : Fragment() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        // Inflate the layout for this fragment
        return inflater.inflate(R.layout.fragment_naming, container, false)
    }

    var txt: TextInputLayout? = null
    var fab: FloatingActionButton? = null
    var block: ConditionVariable? = null

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {

        txt = view.findViewById(R.id.name_lay)
        fab = view.findViewById(R.id.fab_naming)

        fab!!.setOnClickListener {
            block?.open()
        }

        txt!!.editText!!.maxLines = 1
        txt!!.editText!!.inputType = InputType.TYPE_CLASS_TEXT
        txt!!.editText!!.isSingleLine = true

        txt!!.editText!!.setOnEditorActionListener { v, actionId, event ->
            if(actionId == EditorInfo.IME_ACTION_DONE){
                block?.open()
                true
            } else {
                false
            }
        }

        fun View.focusAndShowKeyboard() {
            /**
             * This is to be called when the window already has focus.
             */
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

        txt!!.editText!!.focusAndShowKeyboard()

        super.onViewCreated(view, savedInstanceState)
    }

    fun setBlockvar(cv: ConditionVariable) {
        block = cv
    }

    fun getResult() : String {
        return txt!!.editText!!.text.toString()
    }

    companion object {
        /**
         * Use this factory method to create a new instance of
         * this fragment using the provided parameters.
         *
         * @param param1 Parameter 1.
         * @param param2 Parameter 2.
         * @return A new instance of fragment NamingFragment.
         */
        // TODO: Rename and change types and number of parameters
        @JvmStatic
        fun newInstance() =
            NamingFragment().apply {
            }
    }
}