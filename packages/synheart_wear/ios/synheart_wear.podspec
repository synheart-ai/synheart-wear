Pod::Spec.new do |s|
  s.name             = 'synheart_wear'
  s.version          = '0.1.0'
  s.summary          = 'Unified wearable SDK for Synheart'
  s.description      = 'Cross-device, cross-platform biometric data normalization'
  s.homepage         = 'https://github.com/synheart-ai/synheart_wear'
  s.license          = { :file => '../LICENSE' }
  s.author           = { 'Synheart AI' => 'team@synheart.ai' }
  s.source           = { :path => '.' }
  s.source_files = 'Classes/**/*'
  s.dependency 'Flutter'
  s.platform = :ios, '11.0'
  s.swift_version = '5.0'
end