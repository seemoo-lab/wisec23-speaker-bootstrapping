package de.seemoo.sonar

import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.widget.Button

class FirstUseActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_first_use)

        findViewById<Button>(R.id.first_use_btn).setOnClickListener {
            finish()
        }
    }
}