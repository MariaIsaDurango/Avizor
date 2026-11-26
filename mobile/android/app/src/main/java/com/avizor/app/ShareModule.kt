package com.avizor.app

import com.facebook.react.bridge.Arguments
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

  @ReactMethod
  fun getSharedFile(promise: Promise) {
    val uri = MainActivity.pendingSharedUri
    val mimeType = MainActivity.pendingSharedMimeType
    if (uri != null && mimeType != null) {
      MainActivity.pendingSharedUri = null
      MainActivity.pendingSharedMimeType = null
      val map = Arguments.createMap().apply {
        putString("uri", uri)
        putString("mimeType", mimeType)
      }
      promise.resolve(map)
    } else {
      promise.resolve(null)
    }
  }
}
