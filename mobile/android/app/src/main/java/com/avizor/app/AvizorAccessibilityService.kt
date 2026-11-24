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
        private const val MIN_EMAIL_LENGTH = 100
        private const val MAX_EMAIL_LENGTH = 5000
        private const val DEBOUNCE_MS = 1500L
        private const val MAX_HASH_CACHE = 100

        // Nodo presente en la vista de detalle del email (aparece en ambos estados de carga).
        // conversation_container desaparece al cargar el email; reply_button persiste.
        // ID verificado en OPPO CPH2783 con Gmail 2024.
        private const val GMAIL_EMAIL_VIEW_ID = "com.google.android.gm:id/reply_button"
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
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED,
            AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> {
                currentEmailPkg = pkg
                handler.removeCallbacks(extractRunnable)
                handler.postDelayed(extractRunnable, DEBOUNCE_MS)
            }
        }
    }

    private fun tryExtractAndEmitEmail() {
        val pkg = currentEmailPkg ?: return
        val root = rootInActiveWindow ?: return
        try {
            // Verificar que estamos en la vista de detalle del email, no en la bandeja.
            if (pkg == GMAIL) {
                val nodes = root.findAccessibilityNodeInfosByViewId(GMAIL_EMAIL_VIEW_ID)
                val inEmailView = !nodes.isNullOrEmpty()
                nodes?.forEach { it.recycle() }
                if (!inEmailView) return
            }

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
        if (direct.isNotEmpty()) return direct.mapNotNull { it?.toString() }.joinToString(" ")
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
