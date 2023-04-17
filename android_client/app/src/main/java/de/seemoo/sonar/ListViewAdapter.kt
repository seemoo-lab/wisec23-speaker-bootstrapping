package de.seemoo.sonar

import androidx.recyclerview.widget.RecyclerView
import android.app.ProgressDialog
import android.view.ViewGroup
import android.view.LayoutInflater
import android.annotation.SuppressLint
import android.content.Context
import android.content.DialogInterface
import android.content.Intent
import android.graphics.Color
import android.graphics.PorterDuff
import android.opengl.Visibility
import android.util.Log
import android.view.View
import android.widget.TextView
import androidx.cardview.widget.CardView
import android.widget.LinearLayout
import android.widget.ImageButton
import android.widget.ImageView
import androidx.appcompat.app.AlertDialog
import androidx.core.content.ContextCompat.getColor
import androidx.core.content.ContextCompat.startActivity
import androidx.lifecycle.LifecycleCoroutineScope
import androidx.lifecycle.lifecycleScope
import androidx.room.Room
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

data class Speaker(val uuid: String, val available: Boolean, val paired: Boolean, val ip: String, val name: String)

class ListViewAdapter internal constructor(private val sketchList: List<Speaker>, private val lsc: LifecycleCoroutineScope, private val ma: MainActivity) :
    RecyclerView.Adapter<ListViewAdapter.ViewHolder>() {
    private var context: Context? = null
    private val oldName: String? = null
    private val dialog: ProgressDialog? = null
    fun dialogAway() {
        if (dialog != null && dialog.isShowing) dialog.dismiss()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view =
            LayoutInflater.from(parent.context).inflate(R.layout.spk_list_element, parent, false)
        val viewHolder: ViewHolder = ViewHolder(view)
        context = parent.context
        return viewHolder
    }

    @SuppressLint("SetTextI18n")
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val sp = sketchList[position];

        holder.txtName.text = sp.name
        if(sp.paired)
            holder.imgSketch.setImageDrawable(context!!.getDrawable(R.drawable.lock))
        else
            holder.imgSketch.setImageDrawable(context!!.getDrawable(R.drawable.unlock))
        holder.txtIP.text = sp.uuid + "\n" + sp.ip

        if(!sp.available)
            holder.cv.background.setTint(getColor(context!!, R.color.card_off))
        else
            holder.cv.background.setTint(getColor(context!!, R.color.card_on))
        if(!sp.paired)
            holder.deleteSketch.visibility = View.INVISIBLE
        else
            holder.deleteSketch.visibility = View.VISIBLE
        holder.cv.setOnClickListener {

            val spk = sketchList[holder.absoluteAdapterPosition]

            if(spk.available && !spk.paired) {
                Log.d("Adapter", "Starting pairing")
                val switchActivityIntent = Intent(context, ConnectingActivity::class.java)
                switchActivityIntent.putExtra("ini", false)
                switchActivityIntent.putExtra("ip", spk.ip)
                switchActivityIntent.putExtra("name", spk.name)
                switchActivityIntent.putExtra("uuid", spk.uuid)
                context?.startActivity(switchActivityIntent)
            }

            if(spk.available && spk.paired) {
                Log.d("Adapter", "Starting control")
                val switchActivityIntent = Intent(context, ControlActivity::class.java)
                switchActivityIntent.putExtra("ip", spk.ip)
                switchActivityIntent.putExtra("uuid", spk.uuid)
                context?.startActivity(switchActivityIntent)
            }

            //dialog = new ProgressDialog(context);
            //dialog.setMessage(context.getResources().getString(R.string.loading));
            //dialog.show();
            //Intent intent = new Intent(context, SketchWidget.class);
            //intent.putExtra("loadFile", sketch.getName());
            //intent.putExtra("name", sketch.getName());
            //context.startActivity(intent);
        }
        holder.deleteSketch.setOnClickListener(object : View.OnClickListener {
            override fun onClick(view: View) {
                val builder = AlertDialog.Builder(
                    context!!
                )
                builder.setMessage(context!!.resources.getString(R.string.sure_delete))
                    .setPositiveButton(R.string.ok, dialogClickListener)
                    .setNegativeButton(R.string.cancel, dialogClickListener).show()
            }

            var dialogClickListener = DialogInterface.OnClickListener { dialog, which ->
                when (which) {
                    DialogInterface.BUTTON_POSITIVE -> {



                        lsc.launch(Dispatchers.IO) {
                            //drop from db
                            val db = Room.databaseBuilder(
                                context!!,
                                UserStore.UserDB::class.java, "userstore"
                            ).enableMultiInstanceInvalidation().build()
                            val uuid = sketchList[holder.absoluteAdapterPosition].uuid
                            db.userDao().remove(uuid)

                            ma.updateList()
                        }
                    }
                    DialogInterface.BUTTON_NEGATIVE -> {}
                }
            }
        })
    }

    override fun getItemCount(): Int {
        return sketchList.size
    }

    inner class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        var imgSketch: ImageView
        var txtName: TextView
        var txtIP: TextView
        var cv: CardView
        var ll: LinearLayout
        var deleteSketch: ImageButton

        init {
            imgSketch = itemView.findViewById(R.id.image_sketch)
            txtName = itemView.findViewById(R.id.text_sketch_name)
            txtIP = itemView.findViewById(R.id.text_last_edited)
            cv = itemView.findViewById(R.id.cardview_sketch)
            ll = itemView.findViewById(R.id.sketch_layout)
            deleteSketch = itemView.findViewById(R.id.btn_sketch_delete)
        }
    }
}