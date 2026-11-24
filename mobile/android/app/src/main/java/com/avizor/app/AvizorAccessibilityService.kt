package com.avizor.app

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class AvizorAccessibilityService : AccessibilityService() {

    companion object {
        const val ACTION_TEXT_EVENT = "com.avizor.app.ACCESSIBILITY_TEXT_EVENT"
        const val EXTRA_TEXT = "text"
        const val EXTRA_PACKAGE = "packageName"
        const val EXTRA_EVENT_TYPE = "eventType"

        private const val GMAIL = "com.google.android.gm"
        private const val OUTLOOK = "com.microsoft.office.outlook"
        private const val MIN_EMAIL_LENGTH = 200
        private const val MAX_EMAIL_LENGTH = 5000
        private const val DEBOUNCE_MS = 1500L
        private const val MAX_HASH_CACHE = 100

        // Clases de Gmail/Outlook que corresponden a la lista de correos, no al detalle.
        private val INBOX_CLASS_KEYWORDS = listOf("ConversationList", "MailList", "InboxList")
    }

    private val analyzedHashes = LinkedHashSet<Int>()
    private var currentEmailPkg: String? = null
    private val handler = Handler(Looper.getMainLooper())
    private val extractRunnable = Runnable { tryExtractAndEmitEmail() }

    override fun onServiceConnected() {
        serviceInfo = serviceInfo.apply {
            eventTypes = AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED or
                AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED or
                AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED or
                AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            notificationTimeout = 100
            flags = AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        if (event.isPassword) return
        val pkg = event.packageName?.toString() ?: return
        if (pkg == packageName) return

        if (pkg == GMAIL || pkg == OUTLOOK) {
            handleEmailApp(event, pkg)
            return
        }

        val text = extractText(event)
        if (text.isNullOrBlank()) return
        emitTextEvent(text, pkg, AccessibilityEvent.eventTypeToString(event.eventType))
    }

    private fun handleEmailApp(event: AccessibilityEvent, pkg: String) {
        when (event.eventType) {
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> {
                val className = event.className?.toString() ?: ""
                // Ignorar la bandeja de entrada y vistas de lista.
                if (INBOX_CLASS_KEYWORDS.any { className.contains(it, ignoreCase = true) }) return
                currentEmailPkg = pkg
                handler.removeCallbacks(extractRunnable)
                handler.postDelayed(extractRunnable, DEBOUNCE_MS)
            }
            AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> {
                if (currentEmailPkg == pkg) {
                    handler.removeCallbacks(extractRunnable)
                    handler.postDelayed(extractRunnable, DEBOUNCE_MS)
                }
            }
        }
    }

    private fun tryExtractAndEmitEmail() {
        val pkg = currentEmailPkg ?: return
        val root = rootInActiveWindow ?: return
        try {
            val body = extractNodeText(root).trim().take(MAX_EMAIL_LENGTH)
            if (body.length < MIN_EMAIL_LENGTH) return
            val hash = body.hashCode()
            if (!addHash(hash)) return
            emitTextEvent(body, pkg, "email_body")
        } finally {
            root.recycle()
        }
    }

    private fun addHash(hash: Int): Boolean {
        if (!analyzedHashes.add(hash)) return false
        if (analyzedHashes.size > MAX_HASH_CACHE) {
            analyzedHashes.remove(analyzedHashes.first())
        }
        return true
    }

    private fun emitTextEvent(text: String, pkg: String, eventType: String) {
        val intent = Intent(ACTION_TEXT_EVENT).apply {
            putExtra(EXTRA_TEXT, text)
            putExtra(EXTRA_PACKAGE, pkg)
            putExtra(EXTRA_EVENT_TYPE, eventType)
            setPackage(packageName)
        }
        sendBroadcast(intent)
    }

    override fun onInterrupt() {
        handler.removeCallbacks(extractRunnable)
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacks(extractRunnable)
    }

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
