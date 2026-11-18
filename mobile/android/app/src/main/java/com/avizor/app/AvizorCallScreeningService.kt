package com.avizor.app

import android.content.Intent
import android.telecom.Call
import android.telecom.CallScreeningService

class AvizorCallScreeningService : CallScreeningService() {

    companion object {
        const val ACTION_CALL_EVENT = "com.avizor.app.CALL_EVENT"
        const val EXTRA_NUMBER = "number"
        const val EXTRA_DIRECTION = "direction"
    }

    override fun onScreenCall(callDetails: Call.Details) {
        val number = callDetails.handle?.schemeSpecificPart ?: "desconocido"
        val direction = if (callDetails.callDirection == Call.Details.DIRECTION_INCOMING) {
            "incoming"
        } else {
            "outgoing"
        }

        val intent = Intent(ACTION_CALL_EVENT).apply {
            putExtra(EXTRA_NUMBER, number)
            putExtra(EXTRA_DIRECTION, direction)
            setPackage(packageName)
        }
        sendBroadcast(intent)

        // PoC: no bloquear ni rechazar la llamada
        respondToCall(callDetails, CallResponse.Builder().build())
    }
}
