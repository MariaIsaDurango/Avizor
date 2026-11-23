package com.avizor.app

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Intent
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class AvizorAccessibilityService : AccessibilityService() {

    companion object {
        const val ACTION_TEXT_EVENT = "com.avizor.app.ACCESSIBILITY_TEXT_EVENT"
        const val EXTRA_TEXT = "text"
        const val EXTRA_PACKAGE = "packageName"
        const val EXTRA_EVENT_TYPE = "eventType"
    }

    override fun onServiceConnected() {
        serviceInfo = serviceInfo.apply {
            eventTypes = AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED or
                AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED or
                AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            notificationTimeout = 100
            flags = AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        if (event.isPassword) return
        if (event.packageName?.toString() == packageName) return

        val text = extractText(event)
        if (text.isNullOrBlank()) return

        val intent = Intent(ACTION_TEXT_EVENT).apply {
            putExtra(EXTRA_TEXT, text)
            putExtra(EXTRA_PACKAGE, event.packageName?.toString() ?: "")
            putExtra(EXTRA_EVENT_TYPE, AccessibilityEvent.eventTypeToString(event.eventType))
            setPackage(packageName)
        }
        sendBroadcast(intent)
    }

    override fun onInterrupt() {}

    private fun extractText(event: AccessibilityEvent): String? {
        val direct = event.text
        if (direct.isNotEmpty()) return direct.joinToString(" ") { it.toString() }
        val source = event.source ?: return null
        return try {
            extractNodeText(source)
        } finally {
            source.recycle()
        }
    }

    private fun extractNodeText(node: AccessibilityNodeInfo): String {
        val sb = StringBuilder()
        if (!node.text.isNullOrBlank()) sb.append(node.text)
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            try {
                val childText = extractNodeText(child)
                if (childText.isNotBlank()) {
                    if (sb.isNotEmpty()) sb.append(" ")
                    sb.append(childText)
                }
            } finally {
                child.recycle()
            }
        }
        return sb.toString()
    }
}
