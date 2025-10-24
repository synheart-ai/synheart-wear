import 'package:flutter_test/flutter_test.dart';
import 'package:synheart_wear/src/core/encryption_service.dart';

void main() {
  group('EncryptionService Tests', () {
    test('detect encrypted data', () {
      final encryptedData = {
        'encrypted_data': 'test',
        'iv': 'test',
        'algorithm': 'AES-256-CBC',
      };

      expect(EncryptionService.isEncrypted(encryptedData), isTrue);

      final plainData = {'hr': 72};
      expect(EncryptionService.isEncrypted(plainData), isFalse);
    });

    test('encryption service static methods work', () {
      // Test static methods that don't require file system access
      expect(EncryptionService.isEncrypted({'test': 'data'}), isFalse);
      expect(
          EncryptionService.isEncrypted({
            'encrypted_data': 'test',
            'iv': 'test',
            'algorithm': 'AES-256-CBC',
          }),
          isTrue);
    });
  });

  // Note: Integration tests that require file system access for key storage
  // are disabled for CI compatibility. These should be run on actual devices.
}
