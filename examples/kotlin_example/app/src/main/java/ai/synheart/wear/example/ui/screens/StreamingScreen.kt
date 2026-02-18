package ai.synheart.wear.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.BluetoothSearching
import androidx.compose.material.icons.filled.DirectionsWalk
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.LinkOff
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.Monitor
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Timeline
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import ai.synheart.wear.example.UiState
import ai.synheart.wear.example.ui.components.MetricCard
import ai.synheart.wear.example.ui.components.StreamButton
import ai.synheart.wear.example.ui.theme.*

@Composable
fun StreamingScreen(
    uiState: UiState,
    onToggleHR: () -> Unit,
    onToggleHRV: () -> Unit,
    onStopAll: () -> Unit,
    onScanBle: () -> Unit,
    onConnectBle: (String) -> Unit,
    onDisconnectBle: () -> Unit,
    onToggleBleStream: () -> Unit,
) {
    val isAnyStreaming = uiState.isStreamingHR || uiState.isStreamingHRV

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        // Streaming status card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = if (isAnyStreaming) {
                    SynheartGreen.copy(alpha = 0.1f)
                } else {
                    MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                },
            ),
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    imageVector = if (isAnyStreaming) Icons.Default.PlayArrow else Icons.Default.Stop,
                    contentDescription = "Stream status",
                    tint = if (isAnyStreaming) SynheartGreen else SynheartGrey,
                )
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = if (isAnyStreaming) "Streaming Active" else "All Streams Stopped",
                        style = MaterialTheme.typography.titleMedium,
                        color = if (isAnyStreaming) SynheartGreen else SynheartGrey,
                    )
                    if (uiState.lastUpdate.isNotEmpty()) {
                        Text(
                            text = "Last update: ${uiState.lastUpdate}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "Stream Controls",
            style = MaterialTheme.typography.titleLarge,
        )
        Spacer(modifier = Modifier.height(12.dp))

        // Stream control buttons
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            StreamButton(
                label = "Heart Rate",
                icon = Icons.Default.Favorite,
                isActive = uiState.isStreamingHR,
                activeColor = SynheartRed,
                onClick = onToggleHR,
                modifier = Modifier.weight(1f),
            )
            StreamButton(
                label = "HRV",
                icon = Icons.Default.Monitor,
                isActive = uiState.isStreamingHRV,
                activeColor = SynheartPurple,
                onClick = onToggleHRV,
                modifier = Modifier.weight(1f),
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        Button(
            onClick = onStopAll,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = SynheartRedDark),
            enabled = isAnyStreaming,
        ) {
            Icon(Icons.Default.Stop, contentDescription = "Stop all", tint = Color.White)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Stop All Streams", color = Color.White)
        }

        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = "Live Data",
            style = MaterialTheme.typography.titleLarge,
        )

        if (uiState.lastUpdate.isNotEmpty()) {
            Text(
                text = "Updated at ${uiState.lastUpdate}",
                style = MaterialTheme.typography.bodySmall,
                color = SynheartBlue,
                modifier = Modifier
                    .padding(vertical = 4.dp)
                    .background(
                        color = SynheartBlue.copy(alpha = 0.08f),
                        shape = RoundedCornerShape(4.dp),
                    )
                    .padding(horizontal = 8.dp, vertical = 2.dp),
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Metrics grid (2 columns)
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            MetricCard(
                title = "Heart Rate",
                value = uiState.heartRate?.let { "%.0f".format(it) } ?: "--",
                unit = "BPM",
                icon = Icons.Default.Favorite,
                color = SynheartRed,
                modifier = Modifier.weight(1f),
            )
            MetricCard(
                title = "HRV",
                value = uiState.hrv?.let { "%.1f".format(it) } ?: "--",
                unit = "ms",
                icon = Icons.Default.Monitor,
                color = SynheartPurple,
                modifier = Modifier.weight(1f),
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            MetricCard(
                title = "Steps",
                value = uiState.steps?.let { "%.0f".format(it) } ?: "--",
                unit = "steps",
                icon = Icons.Default.DirectionsWalk,
                color = SynheartGreen,
                modifier = Modifier.weight(1f),
            )
            MetricCard(
                title = "Calories",
                value = uiState.calories?.let { "%.0f".format(it) } ?: "--",
                unit = "kcal",
                icon = Icons.Default.LocalFireDepartment,
                color = SynheartOrange,
                modifier = Modifier.weight(1f),
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        // RR Intervals card (full width)
        val rrText = uiState.rrIntervals?.let { intervals ->
            if (intervals.size > 3) {
                intervals.take(3).joinToString(", ") { "%.1f".format(it) } + "…"
            } else {
                intervals.joinToString(", ") { "%.1f".format(it) }
            }
        } ?: "--"

        MetricCard(
            title = "RR Intervals",
            value = rrText,
            unit = "ms",
            icon = Icons.Default.Timeline,
            color = SynheartTeal,
        )

        // ── BLE Heart Rate Monitor ─────────────────────────
        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = "BLE Heart Rate Monitor",
            style = MaterialTheme.typography.titleLarge,
        )
        Spacer(modifier = Modifier.height(12.dp))

        // BLE status card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = if (uiState.bleConnected) {
                    SynheartBlue.copy(alpha = 0.1f)
                } else {
                    MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                },
            ),
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    imageVector = if (uiState.bleConnected) Icons.Default.Bluetooth else Icons.Default.BluetoothSearching,
                    contentDescription = "BLE status",
                    tint = if (uiState.bleConnected) SynheartBlue else SynheartGrey,
                )
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = if (uiState.bleConnected) "Connected: ${uiState.bleDeviceName ?: "BLE Device"}" else "No BLE Device Connected",
                        style = MaterialTheme.typography.titleMedium,
                        color = if (uiState.bleConnected) SynheartBlue else SynheartGrey,
                    )
                    if (uiState.bleHeartRate != null) {
                        Text(
                            text = "BLE HR: ${uiState.bleHeartRate} BPM",
                            style = MaterialTheme.typography.bodySmall,
                            color = SynheartRed,
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Scan / Connect / Disconnect buttons
        if (!uiState.bleConnected) {
            Button(
                onClick = onScanBle,
                modifier = Modifier.fillMaxWidth(),
                enabled = !uiState.isScanning,
                colors = ButtonDefaults.buttonColors(containerColor = SynheartBlue),
            ) {
                if (uiState.isScanning) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        color = Color.White,
                        strokeWidth = 2.dp,
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Scanning...", color = Color.White)
                } else {
                    Icon(Icons.Default.BluetoothSearching, contentDescription = "Scan", tint = Color.White)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Scan for BLE HR Monitors", color = Color.White)
                }
            }

            // Show discovered devices
            if (uiState.bleDevices.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Discovered Devices",
                    style = MaterialTheme.typography.titleSmall,
                )
                Spacer(modifier = Modifier.height(4.dp))
                uiState.bleDevices.forEach { (deviceId, name) ->
                    OutlinedButton(
                        onClick = { onConnectBle(deviceId) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 2.dp),
                    ) {
                        Icon(Icons.Default.Bluetooth, contentDescription = null, tint = SynheartBlue)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(name, modifier = Modifier.weight(1f))
                        Text("Connect", color = SynheartBlue)
                    }
                }
            }
        } else {
            // Connected: show stream toggle and disconnect
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                StreamButton(
                    label = "BLE HR",
                    icon = Icons.Default.Bluetooth,
                    isActive = uiState.isStreamingBleHR,
                    activeColor = SynheartBlue,
                    onClick = onToggleBleStream,
                    modifier = Modifier.weight(1f),
                )
                Button(
                    onClick = onDisconnectBle,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = SynheartGrey),
                ) {
                    Icon(Icons.Default.LinkOff, contentDescription = "Disconnect", tint = Color.White)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Disconnect", color = Color.White)
                }
            }

            // BLE HR metric card
            if (uiState.bleHeartRate != null) {
                Spacer(modifier = Modifier.height(12.dp))
                MetricCard(
                    title = "BLE Heart Rate",
                    value = "${uiState.bleHeartRate}",
                    unit = "BPM",
                    icon = Icons.Default.Bluetooth,
                    color = SynheartBlue,
                )
            }
        }
    }
}
