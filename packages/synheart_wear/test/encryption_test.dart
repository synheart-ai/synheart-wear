import 'package:flutter_test/flutter_test.dart';
import 'package:synheart_wear/src/core/encryption_service.dart';

void main() {
  group('EncryptionService Tests', () {
    setUp(() async {
      await EncryptionService.initialize();
    });
    
    tearDown(() async {
      await EncryptionService.deleteKey();
    });
    
    test('encrypt and decrypt data', () async {
      final testData = {
        'hr': 72,
        'steps': 1000,
        'timestamp': '2025-01-20T10:30:00Z',
      };
      
      final encrypted = await EncryptionService.encryptData(testData);
      expect(encrypted['encrypted_data'], isNotNull);
      expect(encrypted['iv'], isNotNull);
      expect(encrypted['algorithm'], equals('AES-256-CBC'));
      
      final decrypted = await EncryptionService.decryptData(encrypted);
      expect(decrypted, equals(testData));
    });
    
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
  });
}