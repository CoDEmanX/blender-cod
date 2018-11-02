import zipfile
import glob
import os

options = {
    "summary": False
}


def PackageName(name, version):
    if(type(version) is str):
        return "%s_%s.zip" % (name, version)
    else:
        return "%s_v%d.%d.%d.zip" % (name, *version)


pkgFile = PackageName("Blender-CoD", (0, 5, 2))

# Create the package archive
file = zipfile.ZipFile(pkgFile, "w")

# Add the detected files to the archive
for name in glob.iglob("io_scene_cod/**/*.py", recursive=True):
    file.write(name, name, zipfile.ZIP_DEFLATED)

file.close()

# Print a file summary if requested
if(options["summary"]):
    file = zipfile.ZipFile(pkgFile, "r")
    for info in file.infolist():
        print(info.filename, info.date_time,
              info.file_size, info.compress_size)
