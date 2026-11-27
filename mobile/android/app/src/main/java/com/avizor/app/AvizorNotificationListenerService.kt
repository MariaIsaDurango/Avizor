package com.avizor.app

import android.app.Notification
import android.content.Intent
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

class AvizorNotificationListenerService : NotificationListenerService() {

    companion object {
        const val ACTION_NOTIFICATION_EVENT = "com.avizor.app.NOTIFICATION_EVENT"
        const val EXTRA_PACKAGE = "packageName"
        const val EXTRA_TITLE = "title"
        const val EXTRA_TEXT = "text"
        const val EXTRA_CATEGORY = "category"

        private val SMS_PACKAGES = setOf(
            "com.android.mms",
            "com.android.messaging",
            "com.google.android.apps.messaging",
            "com.samsung.android.messaging",
        )

        private val DIALER_PACKAGES = setOf(
            "com.android.dialer",
            "com.google.android.dialer",
            "com.samsung.android.dialer",
            "com.samsung.android.incallui",
        )

        private const val MAX_HASH_CACHE = 100
    }

    private val analyzedHashes = LinkedHashSet<Int>()

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName == packageName) return
        if (sbn.notification.flags and Notification.FLAG_GROUP_SUMMARY != 0) return

        val isSms = sbn.packageName in SMS_PACKAGES
        val isDialer = sbn.packageName in DIALER_PACKAGES
        if (!isSms && !isDialer) return

        val category = sbn.notification.category ?: ""
        // Solo procesar llamadas perdidas del marcador.
        if (isDialer && category != Notification.CATEGORY_MISSED_CALL) return

        val extras = sbn.notification.extras
        val title = extras.getString(Notification.EXTRA_TITLE) ?: ""
        // EXTRA_BIG_TEXT contiene el SMS completo; EXTRA_TEXT puede venir recortado.
        val text = (extras.getCharSequence(Notification.EXTRA_BIG_TEXT)
            ?: extras.getCharSequence(Notification.EXTRA_TEXT))?.toString() ?: ""

        if (title.isBlank() && text.isBlank()) return

        val hash = (title + text).hashCode()
        if (!addHash(hash)) return

        val intent = Intent(ACTION_NOTIFICATION_EVENT).apply {
            putExtra(EXTRA_PACKAGE, sbn.packageName)
            putExtra(EXTRA_TITLE, title)
            putExtra(EXTRA_TEXT, text)
            putExtra(EXTRA_CATEGORY, category)
            setPackage(packageName)
        }
        sendBroadcast(intent)
    }

    private fun addHash(hash: Int): Boolean {
        if (!analyzedHashes.add(hash)) return false
        if (analyzedHashes.size > MAX_HASH_CACHE) {
            analyzedHashes.remove(analyzedHashes.first())
        }
        return true
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {}
}
