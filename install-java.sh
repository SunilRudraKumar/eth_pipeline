   #!/usr/bin/env bash
   set -e
   mkdir -p .jdk
   curl -L https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.3+9/OpenJDK21U-jdk_x64_linux_hotspot_21.0.3_9.tar.gz \
     | tar -xz --strip-components=1 -C .jdk