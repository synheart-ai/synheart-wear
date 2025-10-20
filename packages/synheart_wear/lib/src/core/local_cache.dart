import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import '../core/models.dart';

/// Local caching system for wearable data
class LocalCache {
  static const String _cacheDirName = 'synheart_wear';
  static const String _sessionPrefix = 'session_';
  static const String _metaFileName = 'meta.log';

  /// Store a session of wearable data
  static Future<void> storeSession(WearMetrics data) async {
    try {
      final cacheDir = await _getCacheDirectory();
      final sessionId = _generateSessionId(data);
      final sessionFile = File('${cacheDir.path}/$sessionId.json');
      
      // Encrypt data if enabled (placeholder)
      final encryptedData = await _encryptData(data.toJson());
      
      await sessionFile.writeAsString(jsonEncode(encryptedData));
      
      // Update meta log
      await _updateMetaLog(sessionId, data);
    } catch (e) {
      throw SynheartWearError('Failed to store session: $e');
    }
  }

  /// Retrieve cached sessions for a date range
  static Future<List<WearMetrics>> getCachedSessions({
    DateTime? startDate,
    DateTime? endDate,
    int? limit,
  }) async {
    try {
      final cacheDir = await _getCacheDirectory();
      if (!await cacheDir.exists()) return [];

      final files = await cacheDir
          .list()
          .where((file) => file.path.endsWith('.json'))
          .cast<File>()
          .toList();

      final sessions = <WearMetrics>[];
      
      for (final file in files) {
        try {
          final content = await file.readAsString();
          final jsonData = jsonDecode(content) as Map<String, Object?>;
          
          // Decrypt data if needed (placeholder)
          final decryptedData = await _decryptData(jsonData);
          final metrics = WearMetrics.fromJson(decryptedData);
          
          // Filter by date range
          if (startDate != null && metrics.timestamp.isBefore(startDate)) continue;
          if (endDate != null && metrics.timestamp.isAfter(endDate)) continue;
          
          sessions.add(metrics);
          
          if (limit != null && sessions.length >= limit) break;
        } catch (e) {
          // Skip corrupted files
          continue;
        }
      }
      
      // Sort by timestamp (newest first)
      sessions.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      
      return sessions;
    } catch (e) {
      throw SynheartWearError('Failed to retrieve cached sessions: $e');
    }
  }

  /// Get the most recent cached session
  static Future<WearMetrics?> getLatestSession() async {
    final sessions = await getCachedSessions(limit: 1);
    return sessions.isNotEmpty ? sessions.first : null;
  }

  /// Clear cached data older than specified duration
  static Future<void> clearOldData({Duration maxAge = const Duration(days: 30)}) async {
    try {
      final cacheDir = await _getCacheDirectory();
      if (!await cacheDir.exists()) return;

      final cutoffDate = DateTime.now().subtract(maxAge);
      final files = await cacheDir.list().cast<File>().toList();
      
      for (final file in files) {
        try {
          final stat = await file.stat();
          if (stat.modified.isBefore(cutoffDate)) {
            await file.delete();
          }
        } catch (e) {
          // Skip files that can't be processed
          continue;
        }
      }
    } catch (e) {
      throw SynheartWearError('Failed to clear old data: $e');
    }
  }

  /// Get cache statistics
  static Future<Map<String, Object?>> getCacheStats() async {
    try {
      final cacheDir = await _getCacheDirectory();
      if (!await cacheDir.exists()) {
        return {'total_sessions': 0, 'cache_size_bytes': 0, 'oldest_session': null};
      }

      final files = await cacheDir.list().cast<File>().toList();
      int totalSessions = 0;
      int totalSize = 0;
      DateTime? oldestSession;

      for (final file in files) {
        if (file.path.endsWith('.json')) {
          totalSessions++;
          totalSize += await file.length();
          
          final stat = await file.stat();
          if (oldestSession == null || stat.modified.isBefore(oldestSession)) {
            oldestSession = stat.modified;
          }
        }
      }

      return {
        'total_sessions': totalSessions,
        'cache_size_bytes': totalSize,
        'oldest_session': oldestSession?.toIso8601String(),
      };
    } catch (e) {
      throw SynheartWearError('Failed to get cache stats: $e');
    }
  }

  /// Get cache directory path
  static Future<Directory> _getCacheDirectory() async {
    final appDir = await getApplicationDocumentsDirectory();
    final cacheDir = Directory('${appDir.path}/$_cacheDirName');
    
    if (!await cacheDir.exists()) {
      await cacheDir.create(recursive: true);
    }
    
    return cacheDir;
  }

  /// Generate unique session ID
  static String _generateSessionId(WearMetrics data) {
    final timestamp = data.timestamp.toIso8601String().replaceAll(':', '-');
    return '${_sessionPrefix}${timestamp}_${data.deviceId}';
  }

  /// Update meta log with session information
  static Future<void> _updateMetaLog(String sessionId, WearMetrics data) async {
    try {
      final cacheDir = await _getCacheDirectory();
      final metaFile = File('${cacheDir.path}/$_metaFileName');
      
      final metaEntry = {
        'session_id': sessionId,
        'timestamp': data.timestamp.toIso8601String(),
        'device_id': data.deviceId,
        'source': data.source,
        'metrics_count': data.metrics.length,
      };
      
      final existingContent = await metaFile.exists() ? await metaFile.readAsString() : '';
      final lines = existingContent.split('\n').where((line) => line.isNotEmpty).toList();
      lines.add(jsonEncode(metaEntry));
      
      await metaFile.writeAsString(lines.join('\n'));
    } catch (e) {
      // Meta log failure shouldn't break the main operation
      print('Warning: Failed to update meta log: $e');
    }
  }

  /// Encrypt data (placeholder implementation)
  static Future<Map<String, Object?>> _encryptData(Map<String, Object?> data) async {
    // TODO: Implement actual AES-256 encryption
    // For now, just return the data as-is
    return data;
  }

  /// Decrypt data (placeholder implementation)
  static Future<Map<String, Object?>> _decryptData(Map<String, Object?> encryptedData) async {
    // TODO: Implement actual AES-256 decryption
    // For now, just return the data as-is
    return encryptedData;
  }
}
