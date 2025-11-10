/// WHOOP Cloud Provider for Synheart Wear SDK
/// 
/// Connects to WHOOP cloud API via backend connector service.
/// Implements OAuth flow and data fetching per RFC-0002.

import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

import '../core/models.dart';
import '../core/local_cache.dart';

/// WHOOP Cloud Provider for accessing WHOOP data via backend service
class WhoopProvider {
  final String baseUrl;
  final String? redirectUri;
  String? _accessToken;
  String? _userId;

  WhoopProvider({
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
      Uri.parse('$baseUrl/v1/whoop-cloud/oauth/authorize')
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
      // For now, return - actual implementation would use deep link handler
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
    // For now, this is a placeholder that shows the flow
    // The actual callback would contain code from OAuth redirect
    
    // Example: If callback URL is synheart://oauth/callback?code=XXX&state=YYY
    // You would parse the code and exchange it here
  }

  /// Connect with authorization code (for handling OAuth callback)
  Future<void> connectWithCode(String code, String state, String redirectUri) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/v1/whoop-cloud/oauth/callback'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'code': code,
          'state': state,
          'redirect_uri': redirectUri,
          'vendor': 'whoop',
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = json.decode(response.body);
        _userId = data['user_id'] as String?;
        // Store connection status (access token stored securely on backend)
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

  /// Fetch recovery data collection
  /// 
  /// Fetches recovery records from backend
  Future<Map<String, dynamic>> fetchRecovery({
    DateTime? start,
    DateTime? end,
    int limit = 25,
  }) async {
    if (_userId == null) {
      throw SynheartWearError('Not connected. Call connect() first.');
    }

    try {
      final queryParams = <String, String>{
        'limit': limit.toString(),
      };
      if (start != null) {
        queryParams['start'] = start.toIso8601String();
      }
      if (end != null) {
        queryParams['end'] = end.toIso8601String();
      }

      final response = await http.get(
        Uri.parse('$baseUrl/v1/data/$_userId/recovery')
            .replace(queryParameters: queryParams),
        headers: {
          if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        throw NetworkError('Failed to fetch recovery: ${response.statusCode}');
      }
    } catch (e) {
      if (e is NetworkError || e is SynheartWearError) rethrow;
      throw NetworkError('Failed to fetch recovery data: $e');
    }
  }

  /// Fetch sleep data collection
  Future<Map<String, dynamic>> fetchSleep({
    DateTime? start,
    DateTime? end,
    int limit = 25,
  }) async {
    if (_userId == null) {
      throw SynheartWearError('Not connected. Call connect() first.');
    }

    try {
      final queryParams = <String, String>{
        'limit': limit.toString(),
      };
      if (start != null) {
        queryParams['start'] = start.toIso8601String();
      }
      if (end != null) {
        queryParams['end'] = end.toIso8601String();
      }

      final response = await http.get(
        Uri.parse('$baseUrl/v1/data/$_userId/sleep')
            .replace(queryParameters: queryParams),
        headers: {
          if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        throw NetworkError('Failed to fetch sleep: ${response.statusCode}');
      }
    } catch (e) {
      if (e is NetworkError || e is SynheartWearError) rethrow;
      throw NetworkError('Failed to fetch sleep data: $e');
    }
  }

  /// Fetch workout data collection
  Future<Map<String, dynamic>> fetchWorkouts({
    DateTime? start,
    DateTime? end,
    int limit = 25,
  }) async {
    if (_userId == null) {
      throw SynheartWearError('Not connected. Call connect() first.');
    }

    try {
      final queryParams = <String, String>{
        'limit': limit.toString(),
      };
      if (start != null) {
        queryParams['start'] = start.toIso8601String();
      }
      if (end != null) {
        queryParams['end'] = end.toIso8601String();
      }

      final response = await http.get(
        Uri.parse('$baseUrl/v1/data/$_userId/workouts')
            .replace(queryParameters: queryParams),
        headers: {
          if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        throw NetworkError('Failed to fetch workouts: ${response.statusCode}');
      }
    } catch (e) {
      if (e is NetworkError || e is SynheartWearError) rethrow;
      throw NetworkError('Failed to fetch workout data: $e');
    }
  }

  /// Fetch cycle data collection
  Future<Map<String, dynamic>> fetchCycles({
    DateTime? start,
    DateTime? end,
    int limit = 25,
  }) async {
    if (_userId == null) {
      throw SynheartWearError('Not connected. Call connect() first.');
    }

    try {
      final queryParams = <String, String>{
        'limit': limit.toString(),
      };
      if (start != null) {
        queryParams['start'] = start.toIso8601String();
      }
      if (end != null) {
        queryParams['end'] = end.toIso8601String();
      }

      final response = await http.get(
        Uri.parse('$baseUrl/v1/data/$_userId/cycles')
            .replace(queryParameters: queryParams),
        headers: {
          if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        throw NetworkError('Failed to fetch cycles: ${response.statusCode}');
      }
    } catch (e) {
      if (e is NetworkError || e is SynheartWearError) rethrow;
      throw NetworkError('Failed to fetch cycle data: $e');
    }
  }

  /// Fetch recovery data for a specific ID
  Future<WearMetrics?> fetchRecovery(String recoveryId) async {
    if (_userId == null) {
      throw SynheartWearError('Not connected. Call connect() first.');
    }

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/v1/whoop-cloud/data/$_userId/recovery/$recoveryId'),
        headers: {
          if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return WearMetrics.fromJson(data as Map<String, Object?>);
      } else if (response.statusCode == 404) {
        return null;
      } else {
        throw NetworkError('Failed to fetch recovery: ${response.statusCode}');
      }
    } catch (e) {
      if (e is NetworkError || e is SynheartWearError) rethrow;
      throw NetworkError('Failed to fetch recovery: $e');
    }
  }

  /// Disconnect WHOOP integration
  Future<void> disconnect() async {
    if (_userId == null) return;

    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/v1/whoop-cloud/oauth/disconnect').replace(
          queryParameters: {
            'user_id': _userId!,
            'vendor': 'whoop',
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
  
  /// Set user ID directly (for testing when tokens already exist)
  void setUserId(String userId) {
    _userId = userId;
  }

  /// Save connection status locally
  Future<void> _saveConnectionStatus(String userId) async {
    // Store connection status (simplified - in production, use secure storage)
    await LocalCache.storeMetadata({
      'whoop_user_id': userId,
      'whoop_connected_at': DateTime.now().toIso8601String(),
    });
  }

  /// Clear connection status
  Future<void> _clearConnectionStatus() async {
    await LocalCache.storeMetadata({
      'whoop_user_id': null,
      'whoop_connected_at': null,
    });
  }

  /// Restore connection status from cache
  Future<void> restoreConnection() async {
    final metadata = await LocalCache.getMetadata();
    _userId = metadata['whoop_user_id'] as String?;
  }
}

