//
//  Generated file. Do not edit.
//

// clang-format off

#import "GeneratedPluginRegistrant.h"

#if __has_include(<path_provider_foundation/PathProviderPlugin.h>)
#import <path_provider_foundation/PathProviderPlugin.h>
#else
@import path_provider_foundation;
#endif

#if __has_include(<synheart_wear/SynheartWearPlugin.h>)
#import <synheart_wear/SynheartWearPlugin.h>
#else
@import synheart_wear;
#endif

@implementation GeneratedPluginRegistrant

+ (void)registerWithRegistry:(NSObject<FlutterPluginRegistry>*)registry {
  [PathProviderPlugin registerWithRegistrar:[registry registrarForPlugin:@"PathProviderPlugin"]];
  [SynheartWearPlugin registerWithRegistrar:[registry registrarForPlugin:@"SynheartWearPlugin"]];
}

@end
