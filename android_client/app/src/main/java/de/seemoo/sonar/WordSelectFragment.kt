package de.seemoo.sonar

import android.os.Bundle
import android.os.ConditionVariable
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import de.seemoo.sonar.databinding.WordSelectFragmentBinding
import java.util.*
import java.util.concurrent.ThreadLocalRandom
import kotlin.collections.ArrayList

/**
 * A simple [Fragment] subclass as the second destination in the navigation.
 */
class WordSelectFragment : Fragment() {

    private var _binding: WordSelectFragmentBinding? = null
    private val TAG = "WSFrag"

    // This property is only valid between onCreateView and
    // onDestroyView.
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {

        _binding = WordSelectFragmentBinding.inflate(inflater, container, false)
        return binding.root

    }

    private fun shuffleArray(ar: ArrayList<String>) {
        // If running on Java 6 or older, use `new Random()` on RHS here
        for (i in ar.indices) {
            val index: Int = kotlin.random.Random.nextInt(ar.size-1)

            // Simple swap
            val a = ar[index]
            ar[index] = ar[i]
            ar[i] = a
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    var correct = false

    fun getResult() : Boolean {
        return correct
    }

    fun setTexts(strlist : ArrayList<String>, cvar: ConditionVariable) {

        correct = false
        val golden = strlist[0]
        shuffleArray(strlist)

        //set words
        binding.word1.text = strlist[0]
        binding.word2.text = strlist[1]
        binding.word3.text = strlist[2]
        binding.word4.text = strlist[3]
        binding.word5.text = strlist[4]


        val listener = View.OnClickListener { view ->
            Log.d(TAG, "Eval: ${(view as Button).text} $golden")
            if((view as Button).text == golden) {
                correct = true
                Log.d(TAG, "correct found ${(view as Button).text}")
            }else{
                Log.d(TAG, "incorrect found ${(view as Button).text}")
            }
            cvar.open()
        }

        //kinda bad that code has to be repeated...
        //still I do not know of another way
        binding.word1.setOnClickListener(listener)
        binding.word2.setOnClickListener(listener)
        binding.word3.setOnClickListener(listener)
        binding.word4.setOnClickListener(listener)
        binding.word5.setOnClickListener(listener)
        binding.multWords.setOnClickListener(listener)
        binding.noWord.setOnClickListener(listener)

    }
}