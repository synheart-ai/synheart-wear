/// Garmin Cloud Provider for Synheart Wear SDK
/// 
/// Connects to Garmin Health API via backend connector service.
/// Implements OAuth flow and data fetching per RFC-0002.

import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

import '../core/models.dart';
import '../core/local_cache.dart';

/// Garmin Cloud Provider for accessing Garmin data via backend service
class GarminProvider {
  final String baseUrl;
  final String? redirectUri;
  String? _accessToken;
  String? _userId;

  GarminProvider({
    this.baseUrl = 'https://api.wear.synheart.io',
    this.redirectUri,
  });

  /// Launch OAuth consent flow
  /// 
  /// Opens browser/mobile app for user authorization
  Future<void> connect(BuildContext context) async {
    final state = _userId ?? DateTime.now().millisecondsSinceEpoch.toString();
    final redirectUri = this.redirectUri ?? 'synheart://oauth/callback';
    
    // Get authorization URL from backend
    final authUrlResponse = await http.get(
      Uri.parse('$baseUrl/v1/garmin-cloud/oauth/authorize')
          .replace(queryParameters: {
        'redirect_uri': redirectUri,
        'state': state,
      }),
    );

    if (authUrlResponse.statusCode != 200) {
      throw NetworkError('Failed to get authorization URL: ${authUrlResponse.body}');
    }

    final authData = json.decode(authUrlResponse.body);
    final authorizationUrl = authData['authorization_url'] as String;

    // Launch OAuth flow
    final uri = Uri.parse(authorizationUrl);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
      
      // Wait for callback (in real app, handle deep link)
      await _handleOAuthCallback(context, state, redirectUri);
    } else {
      throw NetworkError('Cannot launch OAuth URL: $authorizationUrl');
    }
  }

  /// Handle OAuth callback (called after user authorizes)
  Future<void> _handleOAuthCallback(
    BuildContext context,
    String state,
    String redirectUri,
  ) async {
    // In production, this would be called from deep link handler
    // The actual callback would contain code from OAuth redirect
  }

  /// Connect with authorization code (for handling OAuth callback)
  Future<void> connectWithCode(String code, String state, String redirectUri) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/v1/garmin-cloud/oauth/callback'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'code': code,
          'state': state,
          'redirect_uri': redirectUri,
          'vendor': 'garmin',
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = json.decode(response.body);
        _userId = data['user_id'] as String?;
        await _saveConnectionStatus(_userId ?? state);
      } else {
        final error = json.decode(response.body);
        throw NetworkError(
          'OAuth exchange failed: ${error['error']?['message'] ?? response.body}',
        );
      }
    } catch (e) {
      if (e is NetworkError) rethrow;
      throw NetworkError('Failed to connect: $e');
    }
  }

  /// Fetch daily summaries for a date range
  Future<List<WearMetrics>> fetchDailies(DateTime start, DateTime end) async {
    if (_userId == null) {
      throw SynheartWearError('Not connected. Call connect() first.');
    }

    try {
      final startSeconds = start.millisecondsSinceEpoch ~/ 1000;
      final endSeconds = end.millisecondsSinceEpoch ~/ 1000;

      final response = await http.get(
        Uri.parse('$baseUrl/v1/garmin-cloud/data/$_userId/dailies').replace(
          queryParameters: {
            'start_time_seconds': startSeconds.toString(),
            'end_time_seconds': endSeconds.toString(),
          },
        ),
        headers: {
          if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as List;
        return data
            .map((d) => _convertGarminDailyToWearMetrics(d as Map<String, Object?>))
            .toList();
      } else {
        throw NetworkError('Failed to fetch dailies: ${response.statusCode}');
      }
    } catch (e) {
      if (e is NetworkError || e is SynheartWearError) rethrow;
      throw NetworkError('Failed to fetch Garmin dailies: $e');
    }
  }

  /// Fetch sleep data for a date range
  Future<List<WearMetrics>> fetchSleeps(DateTime start, DateTime end) async {
    if (_userId == null) {
      throw SynheartWearError('Not connected. Call connect() first.');
    }

    try {
      final startSeconds = start.millisecondsSinceEpoch ~/ 1000;
      final endSeconds = end.millisecondsSinceEpoch ~/ 1000;

      final response = await http.get(
        Uri.parse('$baseUrl/v1/garmin-cloud/data/$_userId/sleeps').replace(
          queryParameters: {
            'start_time_seconds': startSeconds.toString(),
            'end_time_seconds': endSeconds.toString(),
          },
        ),
        headers: {
          if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as List;
        return data
            .map((s) => _convertGarminSleepToWearMetrics(s as Map<String, Object?>))
            .toList();
      } else {
        throw NetworkError('Failed to fetch sleeps: ${response.statusCode}');
      }
    } catch (e) {
      if (e is NetworkError || e is SynheartWearError) rethrow;
      throw NetworkError('Failed to fetch Garmin sleeps: $e');
    }
  }

  /// Fetch activities (workouts) for a date range
  Future<List<WearMetrics>> fetchActivities({
    DateTime? start,
    DateTime? end,
  }) async {
    if (_userId == null) {
      throw SynheartWearError('Not connected. Call connect() first.');
    }

    try {
      final queryParams = <String, String>{};
      if (start != null) {
        queryParams['start_time_seconds'] =
            (start.millisecondsSinceEpoch ~/ 1000).toString();
      }
      if (end != null) {
        queryParams['end_time_seconds'] =
            (end.millisecondsSinceEpoch ~/ 1000).toString();
      }

      final response = await http.get(
        Uri.parse('$baseUrl/v1/garmin-cloud/data/$_userId/activities')
            .replace(queryParameters: queryParams),
        headers: {
          if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as List;
        return data
            .map((a) => _convertGarminActivityToWearMetrics(a as Map<String, Object?>))
            .toList();
      } else {
        throw NetworkError('Failed to fetch activities: ${response.statusCode}');
      }
    } catch (e) {
      if (e is NetworkError || e is SynheartWearError) rethrow;
      throw NetworkError('Failed to fetch Garmin activities: $e');
    }
  }

  /// Disconnect Garmin integration
  Future<void> disconnect() async {
    if (_userId == null) return;

    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/v1/garmin-cloud/oauth/disconnect').replace(
          queryParameters: {
            'user_id': _userId!,
            'vendor': 'garmin',
          },
        ),
      );

      if (response.statusCode == 200 || response.statusCode == 204) {
        _userId = null;
        _accessToken = null;
        await _clearConnectionStatus();
      } else {
        throw NetworkError('Failed to disconnect: ${response.statusCode}');
      }
    } catch (e) {
      if (e is NetworkError) rethrow;
      throw NetworkError('Failed to disconnect: $e');
    }
  }

  /// Check if user is connected
  bool get isConnected => _userId != null;

  /// Get current user ID
  String? get userId => _userId;

  /// Convert Garmin daily summary to WearMetrics
  WearMetrics _convertGarminDailyToWearMetrics(Map<String, Object?> garminData) {
    return WearMetrics(
      timestamp: DateTime.parse(garminData['calendarDate'] as String),
      deviceId: 'garmin_${_userId ?? "unknown"}',
      source: 'garmin',
      metrics: {
        'steps': garminData['steps'] as num?,
        'calories': garminData['activeKilocalories'] as num?,
        'hr': garminData['restingHeartRate'] as num?,
      },
      meta: garminData,
    );
  }

  /// Convert Garmin sleep data to WearMetrics
  WearMetrics _convertGarminSleepToWearMetrics(Map<String, Object?> garminData) {
    return WearMetrics(
      timestamp: DateTime.parse(garminData['sleepStartTimestampGMT'] as String? ?? 
                                 DateTime.now().toIso8601String()),
      deviceId: 'garmin_${_userId ?? "unknown"}',
      source: 'garmin',
      metrics: {
        'hr': garminData['averageSleepStress'] as num?,
      },
      meta: garminData,
    );
  }

  /// Convert Garmin activity to WearMetrics
  WearMetrics _convertGarminActivityToWearMetrics(Map<String, Object?> garminData) {
    final startTime = garminData['startTimeInSeconds'] as int?;
    return WearMetrics(
      timestamp: startTime != null
          ? DateTime.fromMillisecondsSinceEpoch(startTime * 1000)
          : DateTime.now(),
      deviceId: 'garmin_${_userId ?? "unknown"}',
      source: 'garmin',
      metrics: {
        'calories': garminData['activeKilocalories'] as num?,
        'steps': garminData['steps'] as num?,
      },
      meta: garminData,
    );
  }

  /// Save connection status locally
  Future<void> _saveConnectionStatus(String userId) async {
    await LocalCache.storeMetadata({
      'garmin_user_id': userId,
      'garmin_connected_at': DateTime.now().toIso8601String(),
    });
  }

  /// Clear connection status
  Future<void> _clearConnectionStatus() async {
    await LocalCache.storeMetadata({
      'garmin_user_id': null,
      'garmin_connected_at': null,
    });
  }

  /// Restore connection status from cache
  Future<void> restoreConnection() async {
    final metadata = await LocalCache.getMetadata();
    _userId = metadata['garmin_user_id'] as String?;
  }
}

