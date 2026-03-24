// Package bleparser provides a high-performance parser for Bluetooth SIG
// Heart Rate Measurement Characteristic (UUID 0x2A37) payloads.
//
// Specification reference:
// https://www.bluetooth.com/specifications/specs/heart-rate-service-1-0/
package bleparser

import (
	"encoding/binary"
	"fmt"
)

// Flag bitmasks for the Heart Rate Measurement Flags byte (Byte 0).
const (
	flagHRFormat16Bit       byte = 0x01 // Bit 0: 1 = uint16 HR, 0 = uint8 HR
	flagEnergyExpended      byte = 0x08 // Bit 3: Energy Expended field present
	flagRRIntervalPresent   byte = 0x10 // Bit 4: RR-Interval values present
)

// BLEHeartRateData holds the parsed fields from a single Heart Rate
// Measurement characteristic notification. JSON tags are included for
// downstream serialization into the Synheart unified data schema.
type BLEHeartRateData struct {
	HeartRate     uint16 `json:"heart_rate"`
	RRIntervalsMs []int  `json:"rr_intervals_ms,omitempty"`
}

// ParseMeasurement decodes a raw BLE Heart Rate Measurement payload following
// the Bluetooth SIG Heart Rate Service specification (Characteristic 0x2A37).
//
// The flags byte (payload[0]) determines the layout of subsequent fields:
//   - Bit 0 (0x01): Heart rate format — 0 = uint8, 1 = uint16 (Little-Endian).
//   - Bit 3 (0x08): Energy Expended present — 2-byte field to skip.
//   - Bit 4 (0x10): RR-Intervals present — remaining bytes as LE uint16 pairs.
//
// Performance: single-pass cursor, one heap allocation (pre-sized RR slice),
// and integer-only arithmetic in the conversion loop.
func ParseMeasurement(payload []byte) (*BLEHeartRateData, error) {
	if len(payload) < 2 {
		return nil, fmt.Errorf("ble-parser: payload too short to contain heart rate data (%d bytes)", len(payload))
	}

	flags := payload[0]
	offset := 1

	var heartRate uint16
	if flags&flagHRFormat16Bit != 0 {
		if offset+2 > len(payload) {
			return nil, fmt.Errorf("ble-parser: payload truncated reading uint16 heart rate at offset %d", offset)
		}
		heartRate = binary.LittleEndian.Uint16(payload[offset:])
		offset += 2
	} else {
		heartRate = uint16(payload[offset])
		offset++
	}

	// Bit 3: Some sensors (e.g. during workout sessions) include a cumulative
	// Energy Expended field (2 bytes) between the HR value and RR-Intervals.
	// We must advance past it so the RR offset is correct.
	if flags&flagEnergyExpended != 0 {
		if offset+2 > len(payload) {
			return nil, fmt.Errorf("ble-parser: payload truncated reading energy expended field at offset %d", offset)
		}
		offset += 2
	}

	result := &BLEHeartRateData{HeartRate: heartRate}

	if flags&flagRRIntervalPresent != 0 {
		remaining := len(payload) - offset
		if remaining < 2 {
			return nil, fmt.Errorf("ble-parser: payload truncated reading RR-interval at offset %d (%d bytes remaining)", offset, remaining)
		}
		if remaining%2 != 0 {
			return nil, fmt.Errorf("ble-parser: RR-interval region has odd byte count (%d) at offset %d", remaining, offset)
		}

		count := remaining / 2
		result.RRIntervalsMs = make([]int, 0, count)

		for i := 0; i < count; i++ {
			raw := binary.LittleEndian.Uint16(payload[offset:])
			offset += 2
			// Bluetooth SIG defines R-R intervals in units of 1/1024 seconds.
			// Integer division avoids floating-point overhead on embedded targets.
			result.RRIntervalsMs = append(result.RRIntervalsMs, int((uint32(raw)*1000)/1024))
		}
	}

	return result, nil
}
