Pod::Spec.new do |s|
  s.name             = 'synheart_wear'
  s.version          = '0.1.1'
  s.summary          = 'Unified wearable SDK for Synheart (iOS plugin stubs)'
  s.description      = <<-DESC
Synheart Wear iOS plugin for optional HealthKit heartbeat series (RR) integration.
  DESC
  s.homepage         = 'https://github.com/synheart-ai/synheart_wear'
  s.license          = { :file => '../LICENSE' }
  s.author           = { 'Synheart' => 'opensource@synheart.ai' }
  s.source           = { :path => '.' }

  s.source_files = 'Classes/**/*'
  s.dependency 'Flutter'
  s.platform = :ios, '13.0'
  s.swift_version = '5.0'
  s.static_framework = true
end

