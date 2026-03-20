package ai.synheart.wear.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Stream
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.viewmodel.compose.viewModel
import ai.synheart.wear.example.ui.screens.DashboardScreen
import ai.synheart.wear.example.ui.screens.HealthDataScreen
import ai.synheart.wear.example.ui.screens.StreamingScreen
import ai.synheart.wear.example.ui.theme.SynheartWearExampleTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SynheartWearExampleTheme {
                SynheartWearApp()
            }
        }
    }
}

private data class TabItem(
    val title: String,
    val icon: ImageVector,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SynheartWearApp(viewModel: MainViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    var selectedTab by remember { mutableIntStateOf(0) }

    val tabs = listOf(
        TabItem("Dashboard", Icons.Default.Dashboard),
        TabItem("Health Data", Icons.Default.Favorite),
        TabItem("Streaming", Icons.Default.Stream),
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Synheart Wear") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                ),
            )
        },
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
        ) {
            TabRow(selectedTabIndex = selectedTab) {
                tabs.forEachIndexed { index, tab ->
                    Tab(
                        selected = selectedTab == index,
                        onClick = { selectedTab = index },
                        text = { Text(tab.title) },
                        icon = { Icon(tab.icon, contentDescription = tab.title) },
                    )
                }
            }

            when (selectedTab) {
                0 -> DashboardScreen(
                    uiState = uiState,
                    onInitSdk = viewModel::initializeSdk,
                    onRequestPermissions = viewModel::requestPermissions,
                    onReadHealthData = viewModel::readHealthData,
                    onCheckEncryption = viewModel::checkEncryption,
                    onTestHealthConnect = viewModel::testHealthConnect,
                    onLoadCacheStats = viewModel::loadCacheStats,
                    onClearCache = viewModel::clearCache,
                    onLoadCachedSessions = viewModel::loadCachedSessions,
                    onPurgeAllData = viewModel::purgeAllData,
                    onConnectProvider = viewModel::connectProvider,
                    onDisconnectProvider = viewModel::disconnectProvider,
                    onCheckProviderStatus = viewModel::checkProviderStatus,
                )
                1 -> HealthDataScreen(
                    uiState = uiState,
                    onRefresh = viewModel::readHealthData,
                )
                2 -> StreamingScreen(
                    uiState = uiState,
                    onToggleHR = viewModel::toggleHRStream,
                    onToggleHRV = viewModel::toggleHRVStream,
                    onStopAll = viewModel::stopAllStreams,
                    onScanBle = viewModel::scanBleDevices,
                    onConnectBle = viewModel::connectBleDevice,
                    onDisconnectBle = viewModel::disconnectBleDevice,
                    onToggleBleStream = viewModel::toggleBleHRStream,
                )
            }
        }
    }
}
