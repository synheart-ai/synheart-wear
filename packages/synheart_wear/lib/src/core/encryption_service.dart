import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:encrypt/encrypt.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';

/// AES-256 encryption service for local data storage
class EncryptionService {
  static const String _keyFileName = 'synheart_encryption.key';
  static const int _keyLength = 32; // 256 bits

  static Encrypter? _encrypter;
  static IV? _iv;

  /// Initialize encryption service with key management
  static Future<void> initialize() async {
    final key = await _getOrCreateKey();
    _encrypter = Encrypter(AES(key));
    _iv = IV.fromSecureRandom(16); // 128-bit IV
  }

  /// Get or create encryption key
  static Future<Key> _getOrCreateKey() async {
    final keyFile = await _getKeyFile();

    if (await keyFile.exists()) {
      final keyBytes = await keyFile.readAsBytes();
      return Key(keyBytes);
    } else {
      // Generate new key
      final keyBytes = _generateSecureKey();
      await keyFile.writeAsBytes(keyBytes);
      return Key(keyBytes);
    }
  }

  /// Generate cryptographically secure key
  static Uint8List _generateSecureKey() {
    final random = Random.secure();
    return Uint8List.fromList(
        List.generate(_keyLength, (_) => random.nextInt(256)));
  }

  /// Get key file path
  static Future<File> _getKeyFile() async {
    final appDir = await getApplicationDocumentsDirectory();
    return File('${appDir.path}/$_keyFileName');
  }

  /// Encrypt data using AES-256
  static Future<Map<String, Object?>> encryptData(
      Map<String, Object?> data) async {
    if (_encrypter == null || _iv == null) {
      await initialize();
    }

    final jsonString = jsonEncode(data);
    final encrypted = _encrypter!.encrypt(jsonString, iv: _iv!);

    return {
      'encrypted_data': encrypted.base64,
      'iv': _iv!.base64,
      'algorithm': 'AES-256-CBC',
      'timestamp': DateTime.now().toIso8601String(),
    };
  }

  /// Decrypt data using AES-256
  static Future<Map<String, Object?>> decryptData(
      Map<String, Object?> encryptedData) async {
    if (_encrypter == null) {
      await initialize();
    }

    final encryptedString = encryptedData['encrypted_data'] as String;
    final ivString = encryptedData['iv'] as String;

    final encrypted = Encrypted.fromBase64(encryptedString);
    final iv = IV.fromBase64(ivString);

    final decryptedString = _encrypter!.decrypt(encrypted, iv: iv);
    return jsonDecode(decryptedString) as Map<String, Object?>;
  }

  /// Check if data is encrypted
  static bool isEncrypted(Map<String, Object?> data) {
    return data.containsKey('encrypted_data') &&
        data.containsKey('iv') &&
        data.containsKey('algorithm');
  }

  /// Rotate encryption key (for security)
  static Future<void> rotateKey() async {
    final keyFile = await _getKeyFile();
    if (await keyFile.exists()) {
      await keyFile.delete();
    }
    await initialize();
  }

  /// Delete encryption key (for data destruction)
  static Future<void> deleteKey() async {
    final keyFile = await _getKeyFile();
    if (await keyFile.exists()) {
      await keyFile.delete();
    }
    _encrypter = null;
    _iv = null;
  }
}
