pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.PREFER_SETTINGS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "SynheartWearExample"
include(":app")

// Composite build: resolve ai.synheart:synheart-wear from the local SDK repo
includeBuild("../../../synheart-wear-kotlin") {
    dependencySubstitution {
        substitute(module("ai.synheart:synheart-wear")).using(project(":"))
    }
}
