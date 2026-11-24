package com.avizor.app

import android.content.Intent
import android.os.Build
import android.os.Bundle

import com.facebook.react.ReactActivity
import com.facebook.react.ReactActivityDelegate
import com.facebook.react.bridge.Arguments
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint.fabricEnabled
import com.facebook.react.defaults.DefaultReactActivityDelegate
import com.facebook.react.modules.core.DeviceEventManagerModule

import expo.modules.ReactActivityDelegateWrapper

class MainActivity : ReactActivity() {

  companion object {
    var pendingSharedText: String? = null
  }

  override fun onCreate(savedInstanceState: Bundle?) {
    setTheme(R.style.AppTheme)
    super.onCreate(null)
    handleShareIntent(intent)
  }

  override fun onNewIntent(intent: Intent?) {
    super.onNewIntent(intent)
    intent?.let { handleShareIntent(it) }
  }

  private fun handleShareIntent(intent: Intent) {
    if (intent.action != Intent.ACTION_SEND) return
    val text = intent.getStringExtra(Intent.EXTRA_TEXT)?.trim()
    if (text.isNullOrBlank()) return
    pendingSharedText = text
    try {
      val ctx = (application as MainApplication).reactHost.currentReactContext
      if (ctx != null) {
        val params = Arguments.createMap().apply { putString("text", text) }
        ctx.getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
          .emit("ShareIntentReceived", params)
        pendingSharedText = null
      }
    } catch (_: Exception) {
      // React context not ready — ShareModule.getSharedText() picks it up on cold start
    }
  }

  override fun getMainComponentName(): String = "main"

  override fun createReactActivityDelegate(): ReactActivityDelegate {
    return ReactActivityDelegateWrapper(
      this,
      BuildConfig.IS_NEW_ARCHITECTURE_ENABLED,
      object : DefaultReactActivityDelegate(
        this,
        mainComponentName,
        fabricEnabled
      ) {}
    )
  }

  override fun invokeDefaultOnBackPressed() {
    if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.R) {
      if (!moveTaskToBack(false)) {
        super.invokeDefaultOnBackPressed()
      }
      return
    }
    super.invokeDefaultOnBackPressed()
  }
}
