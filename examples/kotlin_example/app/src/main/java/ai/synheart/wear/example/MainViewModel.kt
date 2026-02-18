package ai.synheart.wear.example

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import ai.synheart.wear.SynheartWear
import ai.synheart.wear.config.SynheartWearConfig
import ai.synheart.wear.models.DeviceAdapter
import ai.synheart.wear.models.MetricType
import ai.synheart.wear.models.PermissionType
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class UiState(
    val sdkInitialized: Boolean = false,
    val permissionsGranted: Boolean = false,
    val encryptionEnabled: Boolean = false,
    val isStreamingHR: Boolean = false,
    val isStreamingHRV: Boolean = false,
    val heartRate: Double? = null,
    val hrv: Double? = null,
    val steps: Double? = null,
    val calories: Double? = null,
    val rrIntervals: List<Double>? = null,
    val metricsJson: String = "",
    val lastUpdate: String = "",
    val statusMessage: String = "",
    val cacheStats: String = "",
    // BLE HRM state
    val isScanning: Boolean = false,
    val bleConnected: Boolean = false,
    val bleDevices: List<Pair<String, String>> = emptyList(),
    val bleHeartRate: Int? = null,
    val bleDeviceName: String? = null,
    val isStreamingBleHR: Boolean = false,
    // Wearable provider state
    val providerStatuses: Map<String, Boolean> = emptyMap(),
)

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val sdk = SynheartWear(
        context = application,
        config = SynheartWearConfig(
            enabledAdapters = setOf(DeviceAdapter.HEALTH_CONNECT, DeviceAdapter.BLE_HRM),
            enableLocalCaching = true,
            enableEncryption = true,
            streamInterval = 3000L,
        ),
    )

    private val _uiState = MutableStateFlow(UiState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private var hrJob: Job? = null
    private var hrvJob: Job? = null
    private var bleStreamJob: Job? = null

    init {
        initializeSdk()
    }

    override fun onCleared() {
        super.onCleared()
        hrJob?.cancel()
        hrvJob?.cancel()
        bleStreamJob?.cancel()
        sdk.bleHrm?.dispose()
    }

    fun initializeSdk() {
        viewModelScope.launch {
            try {
                _uiState.update { it.copy(statusMessage = "Initializing...") }
                sdk.initialize()
                _uiState.update {
                    it.copy(
                        sdkInitialized = true,
                        statusMessage = "SDK initialized",
                    )
                }
                // Auto-check permissions after init (matches Flutter behavior)
                checkPermissionStatus()
                checkEncryptionFromCache()
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "Init failed: ${e.message}")
                }
            }
        }
    }

    private fun checkPermissionStatus() {
        viewModelScope.launch {
            try {
                val status = sdk.getPermissionStatus()
                val allGranted = status.values.all { it }
                _uiState.update { it.copy(permissionsGranted = allGranted) }
            } catch (_: Exception) { }
        }
    }

    private fun checkEncryptionFromCache() {
        viewModelScope.launch {
            try {
                val stats = sdk.getCacheStats()
                val enabled = stats["encryption_enabled"] == true
                _uiState.update { it.copy(encryptionEnabled = enabled) }
            } catch (_: Exception) { }
        }
    }

    fun requestPermissions() {
        viewModelScope.launch {
            try {
                val result = sdk.requestPermissions(
                    setOf(
                        PermissionType.HEART_RATE,
                        PermissionType.HRV,
                        PermissionType.STEPS,
                        PermissionType.CALORIES,
                    )
                )
                val allGranted = result.values.all { it }
                _uiState.update {
                    it.copy(
                        permissionsGranted = allGranted,
                        statusMessage = if (allGranted) "Permissions granted" else "Some permissions denied",
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "Permission error: ${e.message}")
                }
            }
        }
    }

    fun readHealthData() {
        viewModelScope.launch {
            try {
                val metrics = sdk.readMetrics(isRealTime = false)
                val hr = metrics.getMetric(MetricType.HR)
                // Try SDNN first, fallback to RMSSD (matches Flutter behavior)
                val hrvVal = metrics.getMetric(MetricType.HRV_SDNN)
                    ?: metrics.getMetric(MetricType.HRV_RMSSD)
                val stepsVal = metrics.getMetric(MetricType.STEPS)
                val calsVal = metrics.getMetric(MetricType.CALORIES)

                _uiState.update {
                    it.copy(
                        heartRate = hr,
                        hrv = hrvVal,
                        steps = stepsVal,
                        calories = calsVal,
                        rrIntervals = metrics.rrIntervals,
                        metricsJson = formatMetricsJson(metrics.toMap()),
                        lastUpdate = java.text.SimpleDateFormat(
                            "HH:mm:ss", java.util.Locale.getDefault()
                        ).format(java.util.Date()),
                        statusMessage = "Health data read",
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "Read error: ${e.message}")
                }
            }
        }
    }

    fun checkEncryption() {
        viewModelScope.launch {
            try {
                val stats = sdk.getCacheStats()
                val enabled = stats["encryption_enabled"] == true
                _uiState.update {
                    it.copy(
                        encryptionEnabled = enabled,
                        statusMessage = "Encryption: ${if (enabled) "Enabled" else "Disabled"}",
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "Encryption check error: ${e.message}")
                }
            }
        }
    }

    fun testHealthConnect() {
        viewModelScope.launch {
            try {
                val status = sdk.getPermissionStatus()
                _uiState.update {
                    it.copy(statusMessage = "Health Connect: ${status.size} permission types checked")
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "Health Connect error: ${e.message}")
                }
            }
        }
    }

    fun loadCacheStats() {
        viewModelScope.launch {
            try {
                val stats = sdk.getCacheStats()
                _uiState.update {
                    it.copy(
                        cacheStats = stats.toString(),
                        statusMessage = "Cache stats loaded",
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "Cache error: ${e.message}")
                }
            }
        }
    }

    fun clearCache() {
        viewModelScope.launch {
            try {
                sdk.clearOldCache(maxAgeMs = 7L * 24 * 60 * 60 * 1000)
                _uiState.update {
                    it.copy(statusMessage = "Cache cleared")
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "Clear cache error: ${e.message}")
                }
            }
        }
    }

    fun loadCachedSessions() {
        viewModelScope.launch {
            try {
                val thirtyDaysAgo = System.currentTimeMillis() - 30L * 24 * 60 * 60 * 1000
                val sessions = sdk.getCachedSessions(startDateMs = thirtyDaysAgo)
                _uiState.update {
                    it.copy(statusMessage = "Cached sessions: ${sessions.size} found")
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "Cached sessions error: ${e.message}")
                }
            }
        }
    }

    fun purgeAllData() {
        viewModelScope.launch {
            try {
                sdk.purgeAllData()
                _uiState.update {
                    it.copy(statusMessage = "All data purged (GDPR)")
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "Purge error: ${e.message}")
                }
            }
        }
    }

    fun toggleHRStream() {
        if (_uiState.value.isStreamingHR) {
            hrJob?.cancel()
            hrJob = null
            _uiState.update { it.copy(isStreamingHR = false, statusMessage = "HR stream stopped") }
        } else {
            hrJob = viewModelScope.launch {
                _uiState.update { it.copy(isStreamingHR = true, statusMessage = "HR stream started") }
                try {
                    sdk.streamHR(intervalMs = 2000).collect { metrics ->
                        val hr = metrics.getMetric(MetricType.HR)
                        val stepsVal = metrics.getMetric(MetricType.STEPS)
                        val calsVal = metrics.getMetric(MetricType.CALORIES)
                        _uiState.update {
                            it.copy(
                                heartRate = hr ?: it.heartRate,
                                steps = stepsVal ?: it.steps,
                                calories = calsVal ?: it.calories,
                                rrIntervals = metrics.rrIntervals ?: it.rrIntervals,
                                lastUpdate = java.text.SimpleDateFormat(
                                    "HH:mm:ss", java.util.Locale.getDefault()
                                ).format(java.util.Date()),
                            )
                        }
                    }
                } catch (e: Exception) {
                    _uiState.update {
                        it.copy(isStreamingHR = false, statusMessage = "HR stream error: ${e.message}")
                    }
                }
            }
        }
    }

    fun toggleHRVStream() {
        if (_uiState.value.isStreamingHRV) {
            hrvJob?.cancel()
            hrvJob = null
            _uiState.update { it.copy(isStreamingHRV = false, statusMessage = "HRV stream stopped") }
        } else {
            hrvJob = viewModelScope.launch {
                _uiState.update { it.copy(isStreamingHRV = true, statusMessage = "HRV stream started") }
                try {
                    sdk.streamHRV(windowMs = 5000).collect { metrics ->
                        val hrvVal = metrics.getMetric(MetricType.HRV_SDNN)
                            ?: metrics.getMetric(MetricType.HRV_RMSSD)
                        _uiState.update {
                            it.copy(
                                hrv = hrvVal ?: it.hrv,
                                rrIntervals = metrics.rrIntervals ?: it.rrIntervals,
                                lastUpdate = java.text.SimpleDateFormat(
                                    "HH:mm:ss", java.util.Locale.getDefault()
                                ).format(java.util.Date()),
                            )
                        }
                    }
                } catch (e: Exception) {
                    _uiState.update {
                        it.copy(isStreamingHRV = false, statusMessage = "HRV stream error: ${e.message}")
                    }
                }
            }
        }
    }

    fun stopAllStreams() {
        hrJob?.cancel()
        hrJob = null
        hrvJob?.cancel()
        hrvJob = null
        _uiState.update {
            it.copy(
                isStreamingHR = false,
                isStreamingHRV = false,
                statusMessage = "All streams stopped",
            )
        }
    }

    // ── BLE HRM ──────────────────────────────────────────────

    fun scanBleDevices() {
        viewModelScope.launch {
            try {
                _uiState.update { it.copy(isScanning = true, statusMessage = "Scanning for BLE HR monitors...") }
                val devices = sdk.bleHrm?.scan(timeoutMs = 10000) ?: emptyList()
                _uiState.update {
                    it.copy(
                        isScanning = false,
                        bleDevices = devices.map { d -> Pair(d.deviceId, d.name ?: "Unknown") },
                        statusMessage = "${devices.size} BLE device(s) found",
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(isScanning = false, statusMessage = "BLE scan error: ${e.message}")
                }
            }
        }
    }

    fun connectBleDevice(deviceId: String) {
        viewModelScope.launch {
            try {
                _uiState.update { it.copy(statusMessage = "Connecting to BLE device...") }
                sdk.bleHrm?.connect(deviceId = deviceId)
                val connected = sdk.bleHrm?.isConnected() ?: false
                _uiState.update {
                    it.copy(
                        bleConnected = connected,
                        bleDeviceName = it.bleDevices.firstOrNull { d -> d.first == deviceId }?.second,
                        statusMessage = if (connected) "BLE device connected" else "BLE connection failed",
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "BLE connect error: ${e.message}")
                }
            }
        }
    }

    fun disconnectBleDevice() {
        viewModelScope.launch {
            try {
                bleStreamJob?.cancel()
                bleStreamJob = null
                sdk.bleHrm?.disconnect()
                _uiState.update {
                    it.copy(
                        bleConnected = false,
                        bleDeviceName = null,
                        bleHeartRate = null,
                        isStreamingBleHR = false,
                        statusMessage = "BLE device disconnected",
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "BLE disconnect error: ${e.message}")
                }
            }
        }
    }

    fun toggleBleHRStream() {
        if (_uiState.value.isStreamingBleHR) {
            bleStreamJob?.cancel()
            bleStreamJob = null
            _uiState.update { it.copy(isStreamingBleHR = false, statusMessage = "BLE HR stream stopped") }
        } else {
            bleStreamJob = viewModelScope.launch {
                _uiState.update { it.copy(isStreamingBleHR = true, statusMessage = "BLE HR stream started") }
                try {
                    sdk.bleHrm?.heartRateFlow?.collect { sample ->
                        _uiState.update {
                            it.copy(
                                bleHeartRate = sample.bpm,
                                lastUpdate = java.text.SimpleDateFormat(
                                    "HH:mm:ss", java.util.Locale.getDefault()
                                ).format(java.util.Date()),
                            )
                        }
                    }
                } catch (e: Exception) {
                    _uiState.update {
                        it.copy(isStreamingBleHR = false, statusMessage = "BLE HR stream error: ${e.message}")
                    }
                }
            }
        }
    }

    // ── Wearable Providers ──────────────────────────────────

    fun connectProvider(adapter: DeviceAdapter) {
        viewModelScope.launch {
            try {
                _uiState.update { it.copy(statusMessage = "Connecting ${adapter.name}...") }
                val provider = sdk.getProvider(adapter)
                val oauthUrl = provider.connect()
                _uiState.update {
                    it.copy(statusMessage = "${adapter.name}: OAuth URL received — open in browser to authorize.")
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "${adapter.name} connect error: ${e.message}")
                }
            }
        }
    }

    fun disconnectProvider(adapter: DeviceAdapter) {
        viewModelScope.launch {
            try {
                val provider = sdk.getProvider(adapter)
                provider.disconnect()
                _uiState.update {
                    val updated = it.providerStatuses.toMutableMap()
                    updated.remove(adapter.name)
                    it.copy(
                        providerStatuses = updated,
                        statusMessage = "${adapter.name} disconnected",
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "${adapter.name} disconnect error: ${e.message}")
                }
            }
        }
    }

    fun checkProviderStatus(adapter: DeviceAdapter) {
        viewModelScope.launch {
            try {
                val provider = sdk.getProvider(adapter)
                val connected = provider.isConnected()
                _uiState.update {
                    val updated = it.providerStatuses.toMutableMap()
                    updated[adapter.name] = connected
                    it.copy(
                        providerStatuses = updated,
                        statusMessage = "${adapter.name}: ${if (connected) "Connected" else "Not connected"}",
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(statusMessage = "${adapter.name} status error: ${e.message}")
                }
            }
        }
    }

    private fun formatMetricsJson(map: Map<String, Any>): String {
        val sb = StringBuilder("{\n")
        map.entries.forEachIndexed { index, (key, value) ->
            sb.append("  \"$key\": ")
            when (value) {
                is Map<*, *> -> {
                    sb.append("{\n")
                    value.entries.forEachIndexed { i, (k, v) ->
                        sb.append("    \"$k\": $v")
                        if (i < value.size - 1) sb.append(",")
                        sb.append("\n")
                    }
                    sb.append("  }")
                }
                is List<*> -> sb.append(value.toString())
                is String -> sb.append("\"$value\"")
                else -> sb.append(value)
            }
            if (index < map.size - 1) sb.append(",")
            sb.append("\n")
        }
        sb.append("}")
        return sb.toString()
    }
}
