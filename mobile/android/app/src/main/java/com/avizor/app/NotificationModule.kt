package com.avizor.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.provider.Settings
import androidx.core.app.NotificationManagerCompat
import com.facebook.react.bridge.*
import com.facebook.react.modules.core.DeviceEventManagerModule

class NotificationModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName() = "AvizorNotification"

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != AvizorNotificationListenerService.ACTION_NOTIFICATION_EVENT) return
            val params = Arguments.createMap().apply {
                putString("packageName", intent.getStringExtra(AvizorNotificationListenerService.EXTRA_PACKAGE) ?: "")
                putString("title", intent.getStringExtra(AvizorNotificationListenerService.EXTRA_TITLE) ?: "")
                putString("text", intent.getStringExtra(AvizorNotificationListenerService.EXTRA_TEXT) ?: "")
            }
            reactApplicationContext
                .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
                .emit("AvizorNotificationEvent", params)
        }
    }

    init {
        val filter = IntentFilter(AvizorNotificationListenerService.ACTION_NOTIFICATION_EVENT)
        reactContext.registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
    }

    @ReactMethod
    fun isServiceEnabled(promise: Promise) {
        val enabled = NotificationManagerCompat
            .getEnabledListenerPackages(reactApplicationContext)
            .contains(reactApplicationContext.packageName)
        promise.resolve(enabled)
    }

    @ReactMethod
    fun openSettings() {
        val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        reactApplicationContext.startActivity(intent)
    }

    @ReactMethod fun addListener(eventName: String) {}
    @ReactMethod fun removeListeners(count: Int) {}
}
