# ![Blender-CoD logo](https://raw.githubusercontent.com/CoDEmanX/blender-cod/master/blender-cod-logo.png) Blender-CoD #
*Blender Add-On for Call of Duty® modding*

Import / export addon for Call of Duty's intermediate model and animation plaintext file formats - no Maya required.

**Download**:  Several download options are available. Choose one of the following:
+ [Official releases](https://github.com/CoDEmanX/blender-cod/releases)
+ [Experimental](https://github.com/CoDEmanX/blender-cod.git) (active development)
+ Checkout with Git

Model, animation and notetrack export to any CoD title:
  * XMODEL_EXPORT v5 (vCoD, CoD:UO)
  * XMODEL_EXPORT v6 (CoD2-CoD7)
  * XANIM_EXPORT v3 (all)
  * NT_EXPORT (CoD5, CoD7)

Use in combination with [Lemon / Lime](http://tom-crowley.co.uk/downloads/) or [Wraith](http://aviacreations.com/wraith/).<br>


***Note: Feature description not up-to-date!***

Experimental import is available for XMODEL_EXPORT v6, but lacks materials, UV mapping etc. Armatures may be imported wrong, weights aren't handled yet.

Original export scripts for Blender 2.4x by Flybynyt<br>
Rewritten scripts for Blender 2.5x and above by CoDEmanX<br>
Contributions by SE2Dev

*2015-05-05: Migrated project from Google Code Project Hosting to GitHub. Addon releases were downloaded 4232x at that time.*

## Introduction ##

Getting new 3D content into Call of Duty games can be expensive, because the official mod tools only include plugins for the commercial 3d modelling software [Maya](http://www.autodesk.com/products/maya/overview) by Autodesk (former Alias). With this addon, you can do it for free!

Blender-CoD is a **free**, **open-source** project and provides a plugin for the as well free and open-source **3D modelling software [Blender](http://www.blender.org/)**.

It adds support for XMODEL_EXPORT v5/v6 and XANIM_EXPORT v3 formats, which can be compiled to xmodels and xanims using the mod tools. All CoD titles are supported for export (Blender -> Asset Manager -> Call of Duty).

You can basically import any supported 3d model into Blender (e.g. Blender files, Wavefront OBJ, Collada DAE, 3ds Max 3DS and more), edit it and finally export it for CoD using the Blender-CoD Add-On.

## Features ##

**Supported CoD-titles** (export only):
  * CoD1 (vCoD)
  * CoD:UO (United Offensive)
  * CoD2
  * CoD4 (Modern Warfare)
  * CoD5 (World at War)
  * CoD7 (Black Ops)


### XMODEL_EXPORT v5/v6 ###
  * Supports mesh export with automatic triangulation
  * Armature export (bones)
  * Vertex colors (v6 only, optionally: use color as alpha)
  * Mesh modifiers except Armature (optional)
  * Armature animation (poses) to xmodel sequences ("Pose animation")
  * Adjustable minimum bone weight (optional)
  * Vertex clean-up (optional)
  * User Interface: File > Export > CoD Xmodel (.XMODEL\_EXPORT)


### XANIM_EXPORT v3 ###
  * Supports armature animation export
  * Frame range and framerate can be specified
  * Notetrack export for all CoD titles (minds frame range settings)
  * User Interface: File > Export > CoD Xanim (.XANIM\_EXPORT)
  
## Requirements ##

  * Blender 2.78 or later - [blender.org](http://www.blender.org/download/)


## Installation ##

  1. Download the archive, but don't unzip it!
      + [Release](https://github.com/CoDEmanX/blender-cod/releases)
      + [Experimental](https://github.com/CoDEmanX/blender-cod/archive/master.zip)
  1. Start Blender
  1. Click menu _`File > User Preferences...`_
  1. Activate the _`Addons`_ section
  1. Ignore an already installed version, it will be overwritten by default
  1. Click _`Install Add-On...`_ button at the bottom
  1. Open the downloaded archive
  1. The following entry should be shown: _`Import-Export: Blender-CoD - Add-On for Call of Duty modding (version)`_<br>If it's not listed, make sure that <b>Testing</b> is selected under "Support Level" in the left sidebar!<br>
<ol><li>Tick the checkbox on the right to enable it<br>
</li><li>Click <i><code>Save As Default</code></i> button at the bottom to enable it permanently<br>
</li><li>You can use the new menu entries now: <i><code>File &gt; Export</code></i> and <i><code>File &gt; Import</code></i></li></ol>

<a href='http://www.youtube.com/watch?v=6SkHz7wrAA8'>Watch video on YouTube</a>

<a href='http://www.youtube.com/watch?feature=player_embedded&v=6SkHz7wrAA8' target='_blank'><img src='http://img.youtube.com/vi/6SkHz7wrAA8/0.jpg' width='425' height=344 /></a>

## Releases ##

| Date | Version | Remarks |
|:-----|:--------|:--------|
| 15-Apr-12 | CoD4 Fastfile WAV Scanner | Extraction tool written in Python released (misc) |
| 12-Apr-12 | Blender-CoD Addon **v0.3.5** (alpha 3) | Added export option: Vertex colors as alpha |
| 01-Apr-12 | Blender-CoD Addon **v0.3.4** (alpha 3) | Mesh import, Bmesh support (requires Blender 2.62.3+) |
| 16-Feb-12 | Blender-CoD Addon **v0.3.3** (alpha 3) | Fixed [issue #5](https://github.com/CoDEmanX/blender-cod/issues/5) |
| 25-Jan-12 | Blender-CoD Addon **v0.3.2** (alpha 3) | Fixed [issue #2](https://github.com/CoDEmanX/blender-cod/issues/2) and [issue #4](https://github.com/CoDEmanX/blender-cod/issues/4) |
| 29-Nov-11 | Blender-CoD Addon **v0.3.1** (alpha 3) | Fixed [issue #3](https://github.com/CoDEmanX/blender-cod/issues/3) |
| 22-Nov-11 | Blender-CoD Addon **v0.3.0** (alpha 3) | vCoD/UO & NT_EXPORT support |
| 09-Oct-11 | Blender-CoD Addon **v0.2.3** (alpha 2) | Fixed [issue #1](https://github.com/CoDEmanX/blender-cod/issues/1) |
| 29-Sep-11 | Blender-CoD Addon **v0.2.2** (alpha 2) | CoD2-CoD7 model & anim export |
| 13-Jul-11 | _Start of project_ | Code testing and rewriting from scratch for Blender 2.5+ |

## Links ##

  * [Official Blender.org tutorial page](http://www.blender.org/education-help/tutorials/) (many good text and video tutorials)
  * [BlenderGuru.com tutorials](http://www.blenderguru.com/) (high quality video tutorials and blog)
  * [BlenderArtists.org Forum tutorials](http://blenderartists.org/forum/forumdisplay.php?32-Tutorials)
  * [Wikibooks Blender tutorial list](http://en.wikibooks.org/wiki/Blender_3D:_Tutorial_Links_List) (some may be outdated, look for Blender 2.5x tutorials)
  * [BlenderNation.com tutorials](http://www.blendernation.com/category/education/tutorials/)
  * [Pixel2Life.com Blender tutorials](http://www.pixel2life.com/tutorials/blender_3d/)
  * [Tutorialized.com Blender tutorials](http://www.tutorialized.com/tutorials/Blender-3d/1)

## Contact ##

If you have questions, problems or want to contribute to the project as a coder or tester,
* create an [issue](https://github.com/CoDEmanX/blender-cod/issues) or
* send a [pull request](https://github.com/CoDEmanX/blender-cod/pulls).
