package ai.synheart.wear.example.ui.components

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import ai.synheart.wear.example.ui.theme.SynheartRedDark

@Composable
fun StreamButton(
    label: String,
    icon: ImageVector,
    isActive: Boolean,
    activeColor: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Button(
        onClick = onClick,
        modifier = modifier,
        colors = ButtonDefaults.buttonColors(
            containerColor = if (isActive) SynheartRedDark else activeColor,
        ),
    ) {
        Icon(
            imageVector = icon,
            contentDescription = label,
            tint = Color.White,
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = if (isActive) "Stop" else label,
            color = Color.White,
        )
    }
}
