g++ -dynamiclib -o libfrmgrab.dylib -Wl,-all_load libfrmgrab.a libz.a libjpeg.a libpng.a libslava.a -framework CoreFoundation -framework IOKit -framework 
CoreServices -lexpat

