package com.avizor.app

import android.app.Activity
import android.app.role.RoleManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import com.facebook.react.bridge.*
import com.facebook.react.modules.core.DeviceEventManagerModule

class CallScreeningModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    companion object {
        private const val REQUEST_ROLE_CODE = 42
    }

    override fun getName() = "AvizorCallScreening"

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != AvizorCallScreeningService.ACTION_CALL_EVENT) return
            val params = Arguments.createMap().apply {
                putString("number", intent.getStringExtra(AvizorCallScreeningService.EXTRA_NUMBER) ?: "")
                putString("direction", intent.getStringExtra(AvizorCallScreeningService.EXTRA_DIRECTION) ?: "")
            }
            reactApplicationContext
                .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
                .emit("AvizorCallEvent", params)
        }
    }

    init {
        val filter = IntentFilter(AvizorCallScreeningService.ACTION_CALL_EVENT)
        reactContext.registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
    }

    @ReactMethod
    fun hasRole(promise: Promise) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            promise.resolve(false)
            return
        }
        val roleManager = reactApplicationContext.getSystemService(RoleManager::class.java)
        promise.resolve(roleManager.isRoleHeld(RoleManager.ROLE_CALL_SCREENING))
    }

    @ReactMethod
    fun requestRole(promise: Promise) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            promise.reject("UNSUPPORTED", "CallScreeningService requires Android 10+")
            return
        }
        val activity = currentActivity
        if (activity == null) {
            promise.reject("NO_ACTIVITY", "No foreground activity")
            return
        }
        val roleManager = reactApplicationContext.getSystemService(RoleManager::class.java)
        if (roleManager.isRoleHeld(RoleManager.ROLE_CALL_SCREENING)) {
            promise.resolve(true)
            return
        }
        val intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING)
        activity.startActivityForResult(intent, REQUEST_ROLE_CODE)
        promise.resolve(null)
    }

    @ReactMethod fun addListener(eventName: String) {}
    @ReactMethod fun removeListeners(count: Int) {}
}
