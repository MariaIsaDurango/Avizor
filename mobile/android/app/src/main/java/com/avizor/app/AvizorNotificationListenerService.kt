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
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName == packageName) return

        val extras = sbn.notification.extras
        val title = extras.getString(Notification.EXTRA_TITLE) ?: ""
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""

        if (title.isBlank() && text.isBlank()) return

        val intent = Intent(ACTION_NOTIFICATION_EVENT).apply {
            putExtra(EXTRA_PACKAGE, sbn.packageName)
            putExtra(EXTRA_TITLE, title)
            putExtra(EXTRA_TEXT, text)
            setPackage(packageName)
        }
        sendBroadcast(intent)
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {}
}
