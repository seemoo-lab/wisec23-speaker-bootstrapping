package de.seemoo.sonar

import androidx.room.*
import androidx.room.RoomDatabase

class UserStore {

    @Entity
    data class User(
        @PrimaryKey val uid: String,
        @ColumnInfo(name = "encrypt") val key_enc: String,
        @ColumnInfo(name = "sign") val key_sig: String,
        @ColumnInfo(name = "verify") val key_ver: String,
        @ColumnInfo(name = "name") val name: String
    )

    @Dao
    interface UserDao {
        @Query("SELECT * FROM user")
        fun getAll(): List<User>

        @Query("SELECT * FROM user WHERE uid=(:userId) LIMIT 1")
        fun getUser(userId: String): User



        @Query("INSERT INTO user VALUES (:uid , :enc , :sig , :ver, :name)")
        fun insert(uid: String, enc: String, sig: String, ver: String, name: String)

        @Query("DELETE FROM user WHERE uid=:uid")
        fun remove(uid: String)

        //@Delete
        //fun delete(user: User)
    }

    @Database(entities = [User::class], version = 1)
    abstract class UserDB : RoomDatabase() {
        abstract fun userDao(): UserDao
    }


}