[app]
title = mercado_v0
package.name = mercadov0
package.domain = org.mercado
source.dir = .
source.include_exts = py
version = 0.1
requirements = python3,kivy==2.3.0,requests,urllib3,idna,charset-normalizer,certifi,beautifulsoup4,soupsieve,typing_extensions
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
