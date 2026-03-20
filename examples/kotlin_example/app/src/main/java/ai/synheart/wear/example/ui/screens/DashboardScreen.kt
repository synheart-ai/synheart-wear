package ai.synheart.wear.example.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.Cached
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.DeleteSweep
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Sensors
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import ai.synheart.wear.example.UiState
import ai.synheart.wear.example.ui.components.ActionButton
import ai.synheart.wear.example.ui.components.StatusCard
import ai.synheart.wear.example.ui.theme.*
import ai.synheart.wear.models.DeviceAdapter

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun DashboardScreen(
    uiState: UiState,
    onInitSdk: () -> Unit,
    onRequestPermissions: () -> Unit,
    onReadHealthData: () -> Unit,
    onCheckEncryption: () -> Unit,
    onTestHealthConnect: () -> Unit,
    onLoadCacheStats: () -> Unit,
    onClearCache: () -> Unit,
    onLoadCachedSessions: () -> Unit,
    onPurgeAllData: () -> Unit,
    onConnectProvider: (DeviceAdapter) -> Unit,
    onDisconnectProvider: (DeviceAdapter) -> Unit,
    onCheckProviderStatus: (DeviceAdapter) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Text(
            text = "Status",
            style = MaterialTheme.typography.titleLarge,
        )
        Spacer(modifier = Modifier.height(12.dp))

        // Status cards in a 2x2 grid
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            StatusCard(
                title = "SDK Status",
                value = if (uiState.sdkInitialized) "Ready" else "Not Init",
                icon = Icons.Default.CheckCircle,
                color = if (uiState.sdkInitialized) SynheartGreen else SynheartOrange,
                modifier = Modifier.weight(1f),
            )
            StatusCard(
                title = "Permissions",
                value = if (uiState.permissionsGranted) "Granted" else "Pending",
                icon = Icons.Default.Security,
                color = if (uiState.permissionsGranted) SynheartGreen else SynheartRed,
                modifier = Modifier.weight(1f),
            )
        }
        Spacer(modifier = Modifier.height(12.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            StatusCard(
                title = "Encryption",
                value = if (uiState.encryptionEnabled) "Enabled" else "Disabled",
                icon = Icons.Default.Lock,
                color = if (uiState.encryptionEnabled) SynheartGreen else SynheartGrey,
                modifier = Modifier.weight(1f),
            )
            StatusCard(
                title = "Streaming",
                value = if (uiState.isStreamingHR || uiState.isStreamingHRV) "Active" else "Idle",
                icon = Icons.Default.Sensors,
                color = if (uiState.isStreamingHR || uiState.isStreamingHRV) SynheartGreen else SynheartGrey,
                modifier = Modifier.weight(1f),
            )
        }

        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = "Quick Actions",
            style = MaterialTheme.typography.titleLarge,
        )
        Spacer(modifier = Modifier.height(12.dp))

        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            ActionButton(
                label = "Initialize SDK",
                icon = Icons.Default.PlayArrow,
                color = SynheartGreen,
                onClick = onInitSdk,
            )
            ActionButton(
                label = "Read Health Data",
                icon = Icons.Default.Favorite,
                color = SynheartRed,
                onClick = onReadHealthData,
            )
            ActionButton(
                label = "Request Permissions",
                icon = Icons.Default.Security,
                color = SynheartOrange,
                onClick = onRequestPermissions,
            )
            ActionButton(
                label = "Check Encryption",
                icon = Icons.Default.Lock,
                color = SynheartIndigo,
                onClick = onCheckEncryption,
            )
            ActionButton(
                label = "Test Health Connect",
                icon = Icons.Default.Sensors,
                color = SynheartGreen,
                onClick = onTestHealthConnect,
            )
            ActionButton(
                label = "Cache Stats",
                icon = Icons.Default.Cached,
                color = SynheartBlue,
                onClick = onLoadCacheStats,
            )
            ActionButton(
                label = "Clear Cache",
                icon = Icons.Default.DeleteSweep,
                color = SynheartGrey,
                onClick = onClearCache,
            )
            ActionButton(
                label = "Cached Sessions",
                icon = Icons.Default.History,
                color = SynheartTeal,
                onClick = onLoadCachedSessions,
            )
            ActionButton(
                label = "Purge All Data",
                icon = Icons.Default.Warning,
                color = SynheartRedDark,
                onClick = onPurgeAllData,
            )
        }

        // ── Wearable Providers ─────────────────────────────
        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = "Wearable Providers",
            style = MaterialTheme.typography.titleLarge,
        )
        Spacer(modifier = Modifier.height(12.dp))

        val cloudProviders = listOf(
            Triple(DeviceAdapter.GARMIN, "Garmin", SynheartGreen),
            Triple(DeviceAdapter.WHOOP, "WHOOP", SynheartIndigo),
            Triple(DeviceAdapter.FITBIT, "Fitbit", SynheartBlue),
        )

        cloudProviders.forEach { (adapter, label, color) ->
            val isConnected = uiState.providerStatuses[adapter.name] == true
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    imageVector = if (isConnected) Icons.Default.Cloud else Icons.Default.CloudOff,
                    contentDescription = label,
                    tint = if (isConnected) color else SynheartGrey,
                )
                Text(
                    text = label,
                    style = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier.weight(1f),
                )
                OutlinedButton(
                    onClick = { onCheckProviderStatus(adapter) },
                ) {
                    Text("Status")
                }
                if (isConnected) {
                    ActionButton(
                        label = "Disconnect",
                        icon = Icons.Default.CloudOff,
                        color = SynheartRedDark,
                        onClick = { onDisconnectProvider(adapter) },
                    )
                } else {
                    ActionButton(
                        label = "Connect",
                        icon = Icons.Default.Cloud,
                        color = color,
                        onClick = { onConnectProvider(adapter) },
                    )
                }
            }
        }

        // BLE status on dashboard
        Spacer(modifier = Modifier.height(12.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = Icons.Default.Bluetooth,
                contentDescription = "BLE",
                tint = if (uiState.bleConnected) SynheartBlue else SynheartGrey,
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = if (uiState.bleConnected) "BLE HRM: ${uiState.bleDeviceName ?: "Connected"}" else "BLE HRM: Not connected",
                style = MaterialTheme.typography.bodyLarge,
                modifier = Modifier.weight(1f),
            )
            Text(
                text = if (uiState.bleConnected) "Active" else "Idle",
                style = MaterialTheme.typography.bodySmall,
                color = if (uiState.bleConnected) SynheartBlue else SynheartGrey,
            )
        }

        if (uiState.statusMessage.isNotEmpty()) {
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = uiState.statusMessage,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            )
        }
    }
}
