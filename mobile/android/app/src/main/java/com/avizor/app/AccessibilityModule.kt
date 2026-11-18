package com.avizor.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.provider.Settings
import com.facebook.react.bridge.*
import com.facebook.react.modules.core.DeviceEventManagerModule

class AccessibilityModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName() = "AvizorAccessibility"

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != AvizorAccessibilityService.ACTION_TEXT_EVENT) return
            val params = Arguments.createMap().apply {
                putString("text", intent.getStringExtra(AvizorAccessibilityService.EXTRA_TEXT) ?: "")
                putString("packageName", intent.getStringExtra(AvizorAccessibilityService.EXTRA_PACKAGE) ?: "")
                putString("eventType", intent.getStringExtra(AvizorAccessibilityService.EXTRA_EVENT_TYPE) ?: "")
            }
            reactApplicationContext
                .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
                .emit("AvizorTextEvent", params)
        }
    }

    init {
        val filter = IntentFilter(AvizorAccessibilityService.ACTION_TEXT_EVENT)
        reactContext.registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
    }

    @ReactMethod
    fun isServiceEnabled(promise: Promise) {
        promise.resolve(checkEnabled())
    }

    @ReactMethod
    fun openSettings() {
        val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        reactApplicationContext.startActivity(intent)
    }

    // Requeridos por RN para NativeEventEmitter
    @ReactMethod fun addListener(eventName: String) {}
    @ReactMethod fun removeListeners(count: Int) {}

    private fun checkEnabled(): Boolean {
        val service = "${reactApplicationContext.packageName}/${AvizorAccessibilityService::class.java.name}"
        return try {
            val enabled = Settings.Secure.getInt(
                reactApplicationContext.contentResolver,
                Settings.Secure.ACCESSIBILITY_ENABLED,
            )
            if (enabled != 1) return false
            val list = Settings.Secure.getString(
                reactApplicationContext.contentResolver,
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
            ) ?: return false
            list.split(":").any { it.equals(service, ignoreCase = true) }
        } catch (e: Exception) {
            false
        }
    }
}
