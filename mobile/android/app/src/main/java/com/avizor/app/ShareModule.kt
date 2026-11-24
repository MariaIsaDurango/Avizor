package com.avizor.app

import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

class ShareModule(reactContext: ReactApplicationContext) :
  ReactContextBaseJavaModule(reactContext) {

  override fun getName() = "ShareModule"

  @ReactMethod
  fun getSharedText(promise: Promise) {
    val text = MainActivity.pendingSharedText
    MainActivity.pendingSharedText = null
    promise.resolve(text)
  }
}
