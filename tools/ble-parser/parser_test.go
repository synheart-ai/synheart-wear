package bleparser

import (
	"slices"
	"testing"
)

// TestParseMeasurement validates parsing of Bluetooth SIG Heart Rate
// Measurement (0x2A37) payloads against known device captures and edge cases.
func TestParseMeasurement(t *testing.T) {
	tests := []struct {
		name    string
		payload []byte
		wantHR  uint16
		wantRR  []int
		wantErr bool
	}{
		{
			name:    "Polar H10",
			payload: []byte{0x14, 0x44, 0x87, 0x03, 0x6E, 0x03},
			wantHR:  68,
			wantRR:  []int{881, 857},
		},
		{
			name:    "Garmin 16-bit",
			payload: []byte{0x15, 0x44, 0x00, 0x87, 0x03},
			wantHR:  68,
			wantRR:  []int{881},
		},
		{
			name:    "Energy Expended Skip",
			payload: []byte{0x1C, 0x44, 0xEE, 0xFF, 0x87, 0x03},
			wantHR:  68,
			wantRR:  []int{881},
		},
		{
			name:    "HR only no RR",
			payload: []byte{0x00, 0x50},
			wantHR:  80,
			wantRR:  nil,
		},
		{
			name:    "Empty payload",
			payload: []byte{},
			wantErr: true,
		},
		{
			name:    "Truncated uint16 HR",
			payload: []byte{0x01, 0x44},
			wantErr: true,
		},
		{
			name:    "Truncated RR",
			payload: []byte{0x10, 0x44, 0x87},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseMeasurement(tt.payload)

			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if got.HeartRate != tt.wantHR {
				t.Errorf("HeartRate = %d, want %d", got.HeartRate, tt.wantHR)
			}

			if !slices.Equal(got.RRIntervalsMs, tt.wantRR) {
				t.Errorf("RRIntervalsMs = %v, want %v", got.RRIntervalsMs, tt.wantRR)
			}
		})
	}
}
