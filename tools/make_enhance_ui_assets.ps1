Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$ErrorActionPreference = 'Stop'
$outDir = Join-Path $PSScriptRoot '..\assets\ui'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

function C([int]$a, [int]$r, [int]$g, [int]$b) {
  [System.Drawing.Color]::FromArgb($a, $r, $g, $b)
}

function RoundedPath([float]$x, [float]$y, [float]$w, [float]$h, [float]$r) {
  $p = New-Object System.Drawing.Drawing2D.GraphicsPath
  $d = $r * 2
  $p.AddArc($x, $y, $d, $d, 180, 90)
  $p.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
  $p.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
  $p.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
  $p.CloseFigure()
  $p
}

function Save-Png($name, [int]$w, [int]$h, [scriptblock]$draw) {
  $bmp = New-Object System.Drawing.Bitmap $w, $h, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.Clear([System.Drawing.Color]::Transparent)
  & $draw $g $w $h
  $path = Join-Path $outDir $name
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose()
  $bmp.Dispose()
}

function Fill-Round($g, $rect, $radius, $top, $bottom, $border, [int]$borderWidth) {
  $path = RoundedPath $rect.X $rect.Y $rect.Width $rect.Height $radius
  $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush $rect, $top, $bottom, 90
  $g.FillPath($brush, $path)
  $brush.Dispose()
  if ($borderWidth -gt 0) {
    $pen = New-Object System.Drawing.Pen $border, $borderWidth
    $g.DrawPath($pen, $path)
    $pen.Dispose()
  }
  $path.Dispose()
}

function Draw-Shine($g, $rect, $radius) {
  $shineRect = New-Object System.Drawing.RectangleF ($rect.X + 5), ($rect.Y + 4), ($rect.Width - 10), ([float]($rect.Height * 0.38))
  $path = RoundedPath $shineRect.X $shineRect.Y $shineRect.Width $shineRect.Height ([Math]::Max(4, $radius - 5))
  $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush $shineRect, (C 118 255 255 255), (C 0 255 255 255), 90
  $g.FillPath($brush, $path)
  $brush.Dispose()
  $path.Dispose()
}

function Draw-Glow($g, $w, $h, $color) {
  $rect = New-Object System.Drawing.RectangleF 0, 0, $w, $h
  $path = New-Object System.Drawing.Drawing2D.GraphicsPath
  $path.AddEllipse($rect)
  $brush = New-Object System.Drawing.Drawing2D.PathGradientBrush $path
  $brush.CenterColor = $color
  $brush.SurroundColors = @((C 0 0 0 0))
  $g.FillEllipse($brush, $rect)
  $brush.Dispose()
  $path.Dispose()
}

function Pt([float]$x, [float]$y) {
  New-Object System.Drawing.PointF $x, $y
}

function StarPath([float]$cx, [float]$cy, [float]$outer, [float]$inner) {
  $path = New-Object System.Drawing.Drawing2D.GraphicsPath
  $pts = New-Object 'System.Drawing.PointF[]' 10
  for ($i = 0; $i -lt 10; $i++) {
    $ang = (-90 + ($i * 36)) * [Math]::PI / 180
    $r = $(if (($i % 2) -eq 0) { $outer } else { $inner })
    $pts[$i] = Pt ($cx + [Math]::Cos($ang) * $r) ($cy + [Math]::Sin($ang) * $r)
  }
  $path.AddPolygon($pts)
  $path
}

function Draw-SoftShadow($g, [System.Drawing.Drawing2D.GraphicsPath]$path, [int]$dx, [int]$dy, [int]$alpha) {
  $m = New-Object System.Drawing.Drawing2D.Matrix
  $m.Translate($dx, $dy)
  $shadow = $path.Clone()
  $shadow.Transform($m)
  $b = New-Object System.Drawing.SolidBrush (C $alpha 0 0 0)
  $g.FillPath($b, $shadow)
  $b.Dispose()
  $shadow.Dispose()
  $m.Dispose()
}

function TextPath-Fit($text, [string]$fontName, [float]$em, [float]$targetX, [float]$targetY, [float]$targetW, [float]$targetH) {
  $family = New-Object System.Drawing.FontFamily $fontName
  $fmt = New-Object System.Drawing.StringFormat ([System.Drawing.StringFormat]::GenericTypographic)
  $fmt.Alignment = [System.Drawing.StringAlignment]::Near
  $fmt.LineAlignment = [System.Drawing.StringAlignment]::Near
  $path = New-Object System.Drawing.Drawing2D.GraphicsPath
  $path.AddString($text, $family, [int][System.Drawing.FontStyle]::Bold, $em, (Pt 0 0), $fmt)
  $bounds = $path.GetBounds()
  $scale = [Math]::Min($targetW / $bounds.Width, $targetH / $bounds.Height)
  $m = New-Object System.Drawing.Drawing2D.Matrix
  $m.Translate(-$bounds.X, -$bounds.Y)
  $m.Scale($scale, $scale, [System.Drawing.Drawing2D.MatrixOrder]::Append)
  $m.Translate($targetX + (($targetW - ($bounds.Width * $scale)) / 2), $targetY + (($targetH - ($bounds.Height * $scale)) / 2), [System.Drawing.Drawing2D.MatrixOrder]::Append)
  $path.Transform($m)
  $m.Dispose()
  $fmt.Dispose()
  $family.Dispose()
  $path
}

Save-Png 'main_title_logo.png' 980 330 {
  param($g, $w, $h)
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  $titleText = ([char]0xC131).ToString() + ([char]0xB530).ToString() + ([char]0xBA39).ToString() + ([char]0xAE30).ToString()

  $banner = New-Object System.Drawing.Drawing2D.GraphicsPath
  $banner.StartFigure()
  $banner.AddBezier((Pt 58 116), (Pt 206 58), (Pt 725 58), (Pt 914 116))
  $banner.AddLine((Pt 938 165), (Pt 902 218))
  $banner.AddBezier((Pt 902 218), (Pt 700 255), (Pt 238 250), (Pt 44 204))
  $banner.AddLine((Pt 70 160), (Pt 58 116))
  $banner.CloseFigure()
  Draw-SoftShadow $g $banner 0 20 156
  Draw-SoftShadow $g $banner 0 7 90

  $bannerRect = New-Object System.Drawing.RectangleF 44, 62, 894, 190
  $bannerFill = New-Object System.Drawing.Drawing2D.LinearGradientBrush $bannerRect, (C 238 176 22 18), (C 238 44 6 7), 90
  $bannerBlend = New-Object System.Drawing.Drawing2D.ColorBlend 6
  $bannerBlend.Positions = @(0.0, 0.18, 0.42, 0.62, 0.82, 1.0)
  $bannerBlend.Colors = @((C 232 235 64 39), (C 224 143 23 18), (C 232 92 8 8), (C 235 42 5 6), (C 230 116 13 10), (C 222 56 7 7))
  $bannerFill.InterpolationColors = $bannerBlend
  $g.FillPath($bannerFill, $banner)
  $bannerFill.Dispose()

  $bannerEdge = New-Object System.Drawing.Pen (C 232 255 211 78), 5
  $bannerEdge.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
  $g.DrawPath($bannerEdge, $banner)
  $bannerEdge.Dispose()

  $bannerInner = New-Object System.Drawing.Drawing2D.GraphicsPath
  $bannerInner.StartFigure()
  $bannerInner.AddBezier((Pt 92 128), (Pt 240 86), (Pt 707 84), (Pt 880 127))
  $bannerInner.AddBezier((Pt 812 218), (Pt 246 218), (Pt 88 178), (Pt 92 128))
  $bannerInner.CloseFigure()
  $innerShade = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 88, 88, 792, 134), (C 80 255 255 210), (C 0 255 255 210), 90
  $g.FillPath($innerShade, $bannerInner)
  $innerShade.Dispose()

  $slashPen = New-Object System.Drawing.Pen (C 34 255 205 77), 2
  foreach ($xLine in @(138, 226, 314, 402, 490, 578, 666, 754)) {
    $g.DrawLine($slashPen, $xLine, 97, ($xLine + 68), 217)
  }
  $slashPen.Dispose()

  $textPath = TextPath-Fit $titleText 'Noto Serif KR Black' 205 70 29 735 202
  $bounds = $textPath.GetBounds()
  Draw-SoftShadow $g $textPath 7 15 190
  Draw-SoftShadow $g $textPath 2 5 124

  for ($step = 14; $step -ge 5; $step -= 3) {
    $m = New-Object System.Drawing.Drawing2D.Matrix
    $m.Translate($step, $step)
    $extrude = $textPath.Clone()
    $extrude.Transform($m)
    $exb = New-Object System.Drawing.SolidBrush (C 210 67 20 2)
    $g.FillPath($exb, $extrude)
    $exb.Dispose()
    $extrude.Dispose()
    $m.Dispose()
  }

  $textOuter = New-Object System.Drawing.Pen (C 255 52 17 2), 25
  $textOuter.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
  $g.DrawPath($textOuter, $textPath)
  $textOuter.Dispose()

  $textRim = New-Object System.Drawing.Pen (C 255 134 49 4), 15
  $textRim.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
  $g.DrawPath($textRim, $textPath)
  $textRim.Dispose()

  $textEdge = New-Object System.Drawing.Pen (C 246 255 231 118), 5
  $textEdge.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
  $g.DrawPath($textEdge, $textPath)
  $textEdge.Dispose()

  $fillRect = New-Object System.Drawing.RectangleF $bounds.X, ($bounds.Y - 14), $bounds.Width, ($bounds.Height + 26)
  $textFill = New-Object System.Drawing.Drawing2D.LinearGradientBrush $fillRect, (C 255 255 248 174), (C 255 193 87 7), 90
  $textBlend = New-Object System.Drawing.Drawing2D.ColorBlend 6
  $textBlend.Positions = @(0.0, 0.18, 0.42, 0.62, 0.82, 1.0)
  $textBlend.Colors = @((C 255 255 255 224), (C 255 255 235 112), (C 255 255 181 39), (C 255 232 110 11), (C 255 255 195 52), (C 255 140 46 3))
  $textFill.InterpolationColors = $textBlend
  $g.FillPath($textFill, $textPath)
  $textFill.Dispose()

  $state = $g.Save()
  $g.SetClip($textPath)
  $shineRect = New-Object System.Drawing.RectangleF ($bounds.X - 4), ($bounds.Y + 4), ($bounds.Width + 8), ([float]($bounds.Height * 0.36))
  $shineBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush $shineRect, (C 125 255 255 238), (C 0 255 255 238), 90
  $g.FillRectangle($shineBrush, $shineRect)
  $shineBrush.Dispose()
  $g.Restore($state)

  $textLight = New-Object System.Drawing.Pen (C 128 255 255 220), 2
  $textLight.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
  $g.DrawPath($textLight, $textPath)
  $textLight.Dispose()

  $sparkPen = New-Object System.Drawing.Pen (C 190 255 247 171), 4
  $g.DrawLine($sparkPen, 148, 77, 168, 70)
  $g.DrawLine($sparkPen, 158, 63, 158, 84)
  $g.DrawLine($sparkPen, 677, 69, 704, 60)
  $g.DrawLine($sparkPen, 691, 50, 691, 78)
  $sparkPen.Dispose()

  $seal = RoundedPath 808 83 100 112 18
  Draw-SoftShadow $g $seal 4 7 126
  $sealRect = New-Object System.Drawing.RectangleF 808, 83, 100, 112
  $sealFill = New-Object System.Drawing.Drawing2D.LinearGradientBrush $sealRect, (C 255 184 28 22), (C 255 76 5 5), 90
  $g.FillPath($sealFill, $seal)
  $sealFill.Dispose()
  $sealPen = New-Object System.Drawing.Pen (C 242 255 213 82), 4
  $sealPen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
  $g.DrawPath($sealPen, $seal)
  $sealPen.Dispose()

  $sealInner = RoundedPath 821 96 74 86 11
  $sealInnerPen = New-Object System.Drawing.Pen (C 132 255 236 156), 2
  $g.DrawPath($sealInnerPen, $sealInner)
  $sealInnerPen.Dispose()
  $sealText = [string]([char]0x6230)
  $sealPath = TextPath-Fit $sealText 'Noto Serif KR Black' 88 828 103 60 68
  $sealBrush = New-Object System.Drawing.SolidBrush (C 238 255 240 185)
  $g.FillPath($sealBrush, $sealPath)
  $sealBrush.Dispose()

  $sealPath.Dispose()
  $sealInner.Dispose()
  $seal.Dispose()
  $textPath.Dispose()
  $bannerInner.Dispose()
  $banner.Dispose()
}

Save-Png 'stat_icon_gold.png' 96 96 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 92 255 192 46)

  $coin = New-Object System.Drawing.RectangleF 14, 13, 68, 68
  $shadow = New-Object System.Drawing.SolidBrush (C 86 0 0 0)
  $g.FillEllipse($shadow, 17, 19, 66, 66)
  $shadow.Dispose()

  $coinBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush $coin, (C 255 255 239 130), (C 255 174 83 9), 115
  $g.FillEllipse($coinBrush, $coin)
  $coinBrush.Dispose()
  $rim = New-Object System.Drawing.Pen (C 255 82 35 3), 5
  $g.DrawEllipse($rim, $coin)
  $rim.Dispose()
  $inner = New-Object System.Drawing.Pen (C 164 255 253 191), 3
  $g.DrawEllipse($inner, 22, 22, 52, 52)
  $inner.Dispose()

  $holeShadow = New-Object System.Drawing.RectangleF 36, 36, 26, 26
  Fill-Round $g $holeShadow 4 (C 255 43 22 5) (C 255 11 7 3) (C 218 255 215 82) 2
  $linePen = New-Object System.Drawing.Pen (C 130 91 38 3), 3
  $g.DrawLine($linePen, 27, 48, 35, 48)
  $g.DrawLine($linePen, 63, 48, 71, 48)
  $g.DrawLine($linePen, 49, 26, 49, 34)
  $g.DrawLine($linePen, 49, 64, 49, 72)
  $linePen.Dispose()
}

Save-Png 'stat_icon_star.png' 96 96 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 84 255 219 87)

  $seal = New-Object System.Drawing.RectangleF 16, 18, 64, 58
  Fill-Round $g $seal 18 (C 255 191 27 20) (C 255 91 6 5) (C 238 255 213 82) 3
  Draw-Shine $g $seal 18
  $ribbon = New-Object System.Drawing.Drawing2D.GraphicsPath
  $ribbon.AddPolygon(@((Pt 28 66), (Pt 42 83), (Pt 49 66), (Pt 56 83), (Pt 70 66)))
  $rb = New-Object System.Drawing.SolidBrush (C 230 87 7 5)
  $g.FillPath($rb, $ribbon)
  $rb.Dispose()
  $ribbon.Dispose()

  $star = StarPath 48 44 25 10.5
  Draw-SoftShadow $g $star 2 4 122
  $starBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 23, 19, 50, 50), (C 255 255 252 167), (C 255 223 130 22), 90
  $g.FillPath($starBrush, $star)
  $starBrush.Dispose()
  $starPen = New-Object System.Drawing.Pen (C 255 88 36 3), 3
  $g.DrawPath($starPen, $star)
  $starPen.Dispose()
  $star.Dispose()
}

Save-Png 'result_star_on.png' 128 128 {
  param($g, $w, $h)

  $halo = StarPath 64 62 57 24
  $haloBrush = New-Object System.Drawing.SolidBrush (C 58 255 205 38)
  $g.FillPath($haloBrush, $halo)
  $haloBrush.Dispose()
  $halo.Dispose()

  $rayPen = New-Object System.Drawing.Pen (C 125 255 215 64), 3
  $rayPen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $rayPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  foreach ($line in @(
    @(64, 8, 64, 24), @(64, 102, 64, 120),
    @(8, 64, 25, 64), @(103, 64, 120, 64),
    @(23, 23, 35, 35), @(93, 93, 105, 105),
    @(23, 105, 35, 93), @(93, 35, 105, 23)
  )) {
    $g.DrawLine($rayPen, $line[0], $line[1], $line[2], $line[3])
  }
  $rayPen.Dispose()

  $star = StarPath 64 62 48 20
  Draw-SoftShadow $g $star 0 8 144

  $rimOuter = New-Object System.Drawing.Pen (C 255 92 32 4), 9
  $rimOuter.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
  $g.DrawPath($rimOuter, $star)
  $rimOuter.Dispose()

  $rimGold = New-Object System.Drawing.Pen (C 255 255 214 57), 5
  $rimGold.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
  $g.DrawPath($rimGold, $star)
  $rimGold.Dispose()

  $pg = New-Object System.Drawing.Drawing2D.PathGradientBrush $star
  $pg.CenterPoint = Pt 56 48
  $pg.CenterColor = C 255 255 255 217
  $pg.SurroundColors = @((C 255 239 116 7))
  $g.FillPath($pg, $star)
  $pg.Dispose()

  $facet = New-Object System.Drawing.Pen (C 105 255 247 164), 2
  $facet.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $facet.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  for ($i = 0; $i -lt 10; $i += 2) {
    $ang = (-90 + ($i * 36)) * [Math]::PI / 180
    $g.DrawLine($facet, 64, 62, (64 + [Math]::Cos($ang) * 38), (62 + [Math]::Sin($ang) * 38))
  }
  $facet.Dispose()

  $shinePath = New-Object System.Drawing.Drawing2D.GraphicsPath
  $shinePath.AddEllipse(42, 27, 34, 18)
  $shineBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 42, 27, 34, 18), (C 120 255 255 255), (C 0 255 255 255), 90
  $g.FillPath($shineBrush, $shinePath)
  $shineBrush.Dispose()
  $shinePath.Dispose()

  $dotBrush = New-Object System.Drawing.SolidBrush (C 190 255 255 216)
  $g.FillEllipse($dotBrush, 80, 30, 8, 8)
  $dotBrush.Dispose()
  $star.Dispose()
}

Save-Png 'result_star_off.png' 128 128 {
  param($g, $w, $h)
  $star = StarPath 64 62 43 18
  Draw-SoftShadow $g $star 0 6 124

  $rim = New-Object System.Drawing.Pen (C 180 40 23 16), 8
  $rim.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
  $g.DrawPath($rim, $star)
  $rim.Dispose()

  $fill = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 21, 19, 86, 86), (C 210 116 96 78), (C 210 46 36 30), 90
  $g.FillPath($fill, $star)
  $fill.Dispose()

  $line = New-Object System.Drawing.Pen (C 62 255 229 172), 2
  $line.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
  $g.DrawPath($line, $star)
  $line.Dispose()
  $star.Dispose()
}

Save-Png 'stat_icon_city.png' 96 96 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 72 255 94 70)

  $shadow = New-Object System.Drawing.SolidBrush (C 92 0 0 0)
  $g.FillEllipse($shadow, 17, 69, 62, 11)
  $shadow.Dispose()

  $wall = New-Object System.Drawing.RectangleF 20, 48, 56, 26
  Fill-Round $g $wall 5 (C 255 185 63 48) (C 255 92 27 18) (C 232 255 205 73) 2
  $gate = New-Object System.Drawing.Drawing2D.GraphicsPath
  $gate.AddArc(36, 54, 24, 34, 180, 180)
  $gate.AddLine(60, 71, 60, 74)
  $gate.AddLine(36, 74, 36, 71)
  $gate.CloseFigure()
  $gb = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 36, 54, 24, 20), (C 255 18 12 8), (C 255 58 26 10), 90
  $g.FillPath($gb, $gate)
  $gb.Dispose()
  $gate.Dispose()

  $tower = New-Object System.Drawing.RectangleF 30, 31, 36, 21
  Fill-Round $g $tower 4 (C 255 218 77 52) (C 255 119 34 20) (C 220 255 218 80) 2
  $roof1 = New-Object System.Drawing.Drawing2D.GraphicsPath
  $roof1.AddPolygon(@((Pt 20 34), (Pt 48 16), (Pt 76 34), (Pt 70 41), (Pt 26 41)))
  $roofBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 20, 16, 56, 25), (C 255 255 221 86), (C 255 93 21 11), 90
  $g.FillPath($roofBrush, $roof1)
  $roofBrush.Dispose()
  $roofPen = New-Object System.Drawing.Pen (C 240 54 16 5), 3
  $g.DrawPath($roofPen, $roof1)
  $roofPen.Dispose()
  $roof1.Dispose()

  $flagPen = New-Object System.Drawing.Pen (C 230 64 24 9), 3
  $g.DrawLine($flagPen, 48, 13, 48, 22)
  $flagPen.Dispose()
  $flag = New-Object System.Drawing.Drawing2D.GraphicsPath
  $flag.AddPolygon(@((Pt 49 13), (Pt 67 17), (Pt 49 22)))
  $fb = New-Object System.Drawing.SolidBrush (C 240 196 23 16)
  $g.FillPath($fb, $flag)
  $fb.Dispose()
  $flag.Dispose()
}

Save-Png 'stat_icon_power.png' 96 96 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 82 166 206 255)

  $bladeBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 19, 12, 58, 58), (C 255 248 250 255), (C 255 105 123 153), 90
  $edgePen = New-Object System.Drawing.Pen (C 230 30 38 54), 3
  $goldPen = New-Object System.Drawing.Pen (C 238 232 166 60), 5
  $redBrush = New-Object System.Drawing.SolidBrush (C 230 145 16 19)
  foreach ($flip in @(0, 1)) {
    $m = New-Object System.Drawing.Drawing2D.Matrix
    if ($flip -eq 0) {
      $m.Translate(48, 48); $m.Rotate(-41); $m.Translate(-48, -48)
    } else {
      $m.Translate(48, 48); $m.Rotate(41); $m.Translate(-48, -48)
    }
    $g.Transform = $m
    $blade = New-Object System.Drawing.Drawing2D.GraphicsPath
    $blade.AddPolygon(@((Pt 44 12), (Pt 52 12), (Pt 56 57), (Pt 48 68), (Pt 40 57)))
    Draw-SoftShadow $g $blade 2 5 94
    $g.FillPath($bladeBrush, $blade)
    $g.DrawPath($edgePen, $blade)
    $blade.Dispose()
    $g.DrawLine($goldPen, 32, 63, 64, 63)
    $g.FillRectangle($redBrush, 43, 64, 10, 20)
    $g.ResetTransform()
    $m.Dispose()
  }
  $pommel = New-Object System.Drawing.Drawing2D.GraphicsPath
  $pommel.AddEllipse(39, 67, 18, 18)
  $pb = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 39, 67, 18, 18), (C 255 255 235 128), (C 255 163 75 10), 90
  $g.FillPath($pb, $pommel)
  $pb.Dispose()
  $pp = New-Object System.Drawing.Pen (C 230 70 27 4), 2
  $g.DrawPath($pp, $pommel)
  $pp.Dispose()
  $pommel.Dispose()
  $bladeBrush.Dispose()
  $edgePen.Dispose()
  $goldPen.Dispose()
  $redBrush.Dispose()
}

Save-Png 'enh_icon_plus.png' 96 96 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 90 255 211 83)
  $rect = New-Object System.Drawing.RectangleF 14, 14, 68, 68
  Fill-Round $g $rect 18 (C 255 255 242 165) (C 255 227 144 31) (C 240 255 255 255) 2
  Draw-Shine $g $rect 18
  $shadow = New-Object System.Drawing.Pen (C 92 69 30 0), 8
  $shadow.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $shadow.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $g.DrawLine($shadow, 48, 28, 48, 68)
  $g.DrawLine($shadow, 28, 48, 68, 48)
  $shadow.Dispose()
  $pen = New-Object System.Drawing.Pen (C 255 61 33 0), 5
  $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $g.DrawLine($pen, 48, 29, 48, 67)
  $g.DrawLine($pen, 29, 48, 67, 48)
  $pen.Dispose()
}

Save-Png 'enh_icon_arrow.png' 96 96 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 105 255 218 99)
  $rect = New-Object System.Drawing.RectangleF 10, 10, 76, 76
  Fill-Round $g $rect 38 (C 255 255 241 158) (C 255 224 132 26) (C 230 255 255 255) 2
  Draw-Shine $g $rect 38
  $shadow = New-Object System.Drawing.Pen (C 94 69 30 0), 8
  $shadow.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $shadow.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $g.DrawLine($shadow, 28, 49, 62, 49)
  $g.DrawLine($shadow, 52, 36, 66, 49)
  $g.DrawLine($shadow, 52, 62, 66, 49)
  $shadow.Dispose()
  $pen = New-Object System.Drawing.Pen (C 255 58 30 0), 5
  $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $g.DrawLine($pen, 27, 47, 62, 47)
  $g.DrawLine($pen, 52, 35, 67, 47)
  $g.DrawLine($pen, 52, 59, 67, 47)
  $pen.Dispose()
}

Save-Png 'enh_icon_remove.png' 64 64 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 72 255 77 58)
  $rect = New-Object System.Drawing.RectangleF 9, 9, 46, 46
  Fill-Round $g $rect 23 (C 255 255 102 88) (C 255 172 12 10) (C 225 255 229 190) 2
  Draw-Shine $g $rect 23
  $shadow = New-Object System.Drawing.Pen (C 90 45 0 0), 7
  $shadow.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $shadow.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $g.DrawLine($shadow, 22, 22, 42, 42)
  $g.DrawLine($shadow, 42, 22, 22, 42)
  $shadow.Dispose()
  $pen = New-Object System.Drawing.Pen (C 255 255 242 196), 4
  $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $g.DrawLine($pen, 21, 21, 43, 43)
  $g.DrawLine($pen, 43, 21, 21, 43)
  $pen.Dispose()
}

Save-Png 'enh_button_primary.png' 640 104 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 80 255 204 63)
  $rect = New-Object System.Drawing.RectangleF 10, 8, ($w - 20), ($h - 18)
  Fill-Round $g $rect 24 (C 255 255 246 178) (C 255 230 143 32) (C 250 255 255 255) 2
  Draw-Shine $g $rect 24
  $inner = New-Object System.Drawing.RectangleF 15, 13, ($w - 30), ($h - 30)
  $pen = New-Object System.Drawing.Pen (C 150 123 58 5), 2
  $g.DrawPath($pen, (RoundedPath $inner.X $inner.Y $inner.Width $inner.Height 19))
  $pen.Dispose()
  $base = New-Object System.Drawing.RectangleF 36, ($h - 21), ($w - 72), 10
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $base, (C 130 124 52 2), (C 0 124 52 2), 0
  $g.FillRectangle($b, $base)
  $b.Dispose()
}

Save-Png 'enh_button_disabled.png' 640 104 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 10, 8, ($w - 20), ($h - 18)
  Fill-Round $g $rect 24 (C 180 77 91 111) (C 180 30 39 56) (C 65 255 255 255) 2
  Draw-Shine $g $rect 24
}

Save-Png 'enh_button_dark.png' 360 76 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 8, 7, ($w - 16), ($h - 14)
  Fill-Round $g $rect 18 (C 235 59 72 92) (C 235 18 26 40) (C 115 255 255 255) 1
  Draw-Shine $g $rect 18
}

Save-Png 'home_tutorial_btn.png' 520 104 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 42 73 125 196)

  $shadow = New-Object System.Drawing.RectangleF 18, 22, ($w - 36), ($h - 30)
  $shadowPath = RoundedPath $shadow.X $shadow.Y $shadow.Width $shadow.Height 34
  $shadowBrush = New-Object System.Drawing.SolidBrush (C 118 0 0 0)
  $g.FillPath($shadowBrush, $shadowPath)
  $shadowBrush.Dispose()
  $shadowPath.Dispose()

  $rect = New-Object System.Drawing.RectangleF 10, 8, ($w - 20), ($h - 22)
  Fill-Round $g $rect 34 (C 248 62 77 98) (C 248 11 18 31) (C 178 255 232 156) 2
  Draw-Shine $g $rect 34

  $rim = New-Object System.Drawing.RectangleF 17, 15, ($w - 34), ($h - 36)
  $rimPen = New-Object System.Drawing.Pen (C 86 255 255 255), 2
  $g.DrawPath($rimPen, (RoundedPath $rim.X $rim.Y $rim.Width $rim.Height 27))
  $rimPen.Dispose()

  $edge = New-Object System.Drawing.RectangleF 34, ($h - 25), ($w - 68), 9
  $edgeBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush $edge, (C 116 255 210 88), (C 0 255 210 88), 0
  $g.FillRectangle($edgeBrush, $edge)
  $edgeBrush.Dispose()

  $glintPath = New-Object System.Drawing.Drawing2D.GraphicsPath
  $glintPath.AddPolygon(@(
    (New-Object System.Drawing.PointF 58, 14),
    (New-Object System.Drawing.PointF 104, 14),
    (New-Object System.Drawing.PointF 68, 76),
    (New-Object System.Drawing.PointF 26, 76)
  ))
  $glintBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 26, 14, 78, 62), (C 88 255 255 255), (C 0 255 255 255), 0
  $g.FillPath($glintBrush, $glintPath)
  $glintBrush.Dispose()
  $glintPath.Dispose()
}

Save-Png 'prison_title_badge.png' 360 92 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 46 255 190 74)
  $rect = New-Object System.Drawing.RectangleF 10, 8, ($w - 20), ($h - 22)
  Fill-Round $g $rect 16 (C 255 227 31 24) (C 255 104 5 3) (C 255 255 205 65) 3
  Draw-Shine $g $rect 16
  $inner = New-Object System.Drawing.RectangleF 20, 18, ($w - 40), ($h - 42)
  $pen = New-Object System.Drawing.Pen (C 150 60 9 4), 2
  $g.DrawPath($pen, (RoundedPath $inner.X $inner.Y $inner.Width $inner.Height 11))
  $pen.Dispose()
  $base = New-Object System.Drawing.RectangleF 38, ($h - 26), ($w - 76), 10
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $base, (C 132 35 3 1), (C 0 35 3 1), 0
  $g.FillRectangle($b, $base)
  $b.Dispose()
}

Save-Png 'prison_star_badge.png' 180 78 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 7, 7, ($w - 14), ($h - 18)
  Fill-Round $g $rect 17 (C 248 48 30 16) (C 248 11 7 4) (C 228 255 195 54) 3
  Draw-Shine $g $rect 17
  $inner = New-Object System.Drawing.RectangleF 16, 16, ($w - 32), ($h - 36)
  $pen = New-Object System.Drawing.Pen (C 94 255 238 164), 1
  $g.DrawPath($pen, (RoundedPath $inner.X $inner.Y $inner.Width $inner.Height 11))
  $pen.Dispose()
}

Save-Png 'prison_face_frame.png' 188 188 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 70 255 197 62)
  $rect = New-Object System.Drawing.RectangleF 10, 10, ($w - 20), ($h - 24)
  Fill-Round $g $rect 28 (C 255 255 222 111) (C 255 103 45 8) (C 238 40 8 3) 3
  Draw-Shine $g $rect 28
  $inner = New-Object System.Drawing.RectangleF 22, 22, ($w - 44), ($h - 48)
  Fill-Round $g $inner 20 (C 255 58 72 89) (C 255 9 15 25) (C 170 255 238 166) 2
}

Save-Png 'prison_speech_panel.png' 760 300 {
  param($g, $w, $h)
  $shadow = New-Object System.Drawing.RectangleF 18, 24, ($w - 36), ($h - 34)
  $shadowPath = RoundedPath $shadow.X $shadow.Y $shadow.Width $shadow.Height 34
  $shadowBrush = New-Object System.Drawing.SolidBrush (C 128 0 0 0)
  $g.FillPath($shadowBrush, $shadowPath)
  $shadowBrush.Dispose()
  $shadowPath.Dispose()

  $rect = New-Object System.Drawing.RectangleF 10, 8, ($w - 20), ($h - 28)
  Fill-Round $g $rect 32 (C 245 255 238 190) (C 245 180 121 55) (C 238 46 12 4) 3
  Draw-Shine $g $rect 32

  $paper = New-Object System.Drawing.RectangleF 25, 23, ($w - 50), ($h - 60)
  $paperBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush $paper, (C 220 255 242 203), (C 220 216 159 86), 90
  $g.FillPath($paperBrush, (RoundedPath $paper.X $paper.Y $paper.Width $paper.Height 22))
  $paperBrush.Dispose()

  $linePen = New-Object System.Drawing.Pen (C 62 104 49 16), 2
  $g.DrawLine($linePen, 42, 92, ($w - 42), 92)
  $g.DrawLine($linePen, 42, 232, ($w - 42), 232)
  $linePen.Dispose()
}

Save-Png 'prison_btn_red.png' 360 92 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 42 255 48 39)
  $rect = New-Object System.Drawing.RectangleF 8, 7, ($w - 16), ($h - 18)
  Fill-Round $g $rect 18 (C 255 236 40 31) (C 255 123 6 4) (C 238 255 210 76) 3
  Draw-Shine $g $rect 18
  $base = New-Object System.Drawing.RectangleF 28, ($h - 22), ($w - 56), 9
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $base, (C 120 39 2 1), (C 0 39 2 1), 0
  $g.FillRectangle($b, $base)
  $b.Dispose()
}

Save-Png 'prison_btn_dark.png' 360 92 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 8, 7, ($w - 16), ($h - 18)
  Fill-Round $g $rect 18 (C 244 57 65 74) (C 244 13 17 26) (C 146 255 214 95) 2
  Draw-Shine $g $rect 18
  $base = New-Object System.Drawing.RectangleF 28, ($h - 22), ($w - 56), 9
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $base, (C 105 0 0 0), (C 0 0 0 0), 0
  $g.FillRectangle($b, $base)
  $b.Dispose()
}

Save-Png 'prison_btn_gold.png' 360 92 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 44 255 210 70)
  $rect = New-Object System.Drawing.RectangleF 8, 7, ($w - 16), ($h - 18)
  Fill-Round $g $rect 18 (C 255 255 244 171) (C 255 223 136 25) (C 240 255 255 255) 2
  Draw-Shine $g $rect 18
  $base = New-Object System.Drawing.RectangleF 28, ($h - 22), ($w - 56), 9
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $base, (C 110 127 55 3), (C 0 127 55 3), 0
  $g.FillRectangle($b, $base)
  $b.Dispose()
}

Save-Png 'enh_tab_active.png' 340 70 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 5, 5, ($w - 10), ($h - 10)
  Fill-Round $g $rect 17 (C 255 255 239 143) (C 255 242 180 55) (C 230 255 255 255) 2
  Draw-Shine $g $rect 17
}

Save-Png 'enh_tab_idle.png' 340 70 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 5, 5, ($w - 10), ($h - 10)
  Fill-Round $g $rect 17 (C 238 55 68 88) (C 238 20 29 44) (C 110 255 255 255) 1
  Draw-Shine $g $rect 17
}

Save-Png 'enh_header_small.png' 150 78 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 6, 6, ($w - 12), ($h - 12)
  Fill-Round $g $rect 18 (C 235 60 78 104) (C 235 27 39 60) (C 115 255 255 255) 1
  Draw-Shine $g $rect 18
}

Save-Png 'enh_header_title.png' 460 78 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 6, 6, ($w - 12), ($h - 12)
  Fill-Round $g $rect 18 (C 245 96 95 76) (C 245 48 51 49) (C 135 255 225 135) 1
  Draw-Shine $g $rect 18
}

Save-Png 'enh_panel_empty.png' 360 360 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 16)
  Fill-Round $g $rect 28 (C 224 43 59 82) (C 224 17 25 41) (C 100 184 210 239) 1
  Draw-Shine $g $rect 28
  $pen = New-Object System.Drawing.Pen (C 92 190 216 244), 2
  $pen.DashPattern = @(4, 5)
  $inner = New-Object System.Drawing.RectangleF 17, 17, ($w - 34), ($h - 34)
  $g.DrawPath($pen, (RoundedPath $inner.X $inner.Y $inner.Width $inner.Height 24))
  $pen.Dispose()
}

Save-Png 'enh_panel_selected.png' 360 360 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 16)
  Fill-Round $g $rect 28 (C 236 64 78 96) (C 236 12 19 33) (C 215 255 218 104) 3
  Draw-Shine $g $rect 28
  Draw-Glow $g $w $h (C 54 255 218 104)
}

Save-Png 'enh_panel_preview.png' 360 360 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 16)
  Fill-Round $g $rect 28 (C 236 35 48 70) (C 236 9 15 27) (C 120 180 214 255) 1
  Draw-Shine $g $rect 28
}

Save-Png 'enh_info_bar.png' 640 60 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 5, 5, ($w - 10), ($h - 10)
  Fill-Round $g $rect 15 (C 224 21 32 49) (C 224 6 13 25) (C 74 206 228 255) 1
}

Save-Png 'enh_fodder_slot.png' 96 96 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 16)
  Fill-Round $g $rect 18 (C 226 40 54 78) (C 226 12 18 31) (C 80 201 222 247) 1
  Draw-Shine $g $rect 18
}

Save-Png 'enh_roster_card.png' 220 330 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 6, 6, ($w - 12), ($h - 12)
  Fill-Round $g $rect 22 (C 244 57 73 98) (C 244 7 13 24) (C 120 207 226 248) 1
  Draw-Shine $g $rect 22
  $art = New-Object System.Drawing.RectangleF 13, 13, ($w - 26), 172
  Fill-Round $g $art 18 (C 86 255 231 146) (C 28 121 214 255) (C 40 255 255 255) 1
  $strip = New-Object System.Drawing.RectangleF 13, 188, ($w - 26), 44
  Fill-Round $g $strip 10 (C 235 16 25 40) (C 235 5 10 20) (C 40 255 255 255) 1
  $info = New-Object System.Drawing.RectangleF 13, 235, ($w - 26), 78
  Fill-Round $g $info 12 (C 170 5 10 18) (C 210 3 6 12) (C 30 255 255 255) 1
}

Save-Png 'enh_roster_card_gold.png' 220 330 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 6, 6, ($w - 12), ($h - 12)
  Fill-Round $g $rect 22 (C 246 70 74 83) (C 246 9 12 20) (C 225 255 218 104) 2
  Draw-Glow $g $w $h (C 40 255 218 104)
  Draw-Shine $g $rect 22
  $art = New-Object System.Drawing.RectangleF 13, 13, ($w - 26), 172
  Fill-Round $g $art 18 (C 105 255 231 146) (C 34 255 180 64) (C 62 255 255 255) 1
  $strip = New-Object System.Drawing.RectangleF 13, 188, ($w - 26), 44
  Fill-Round $g $strip 10 (C 238 20 27 40) (C 238 5 9 18) (C 65 255 218 104) 1
  $info = New-Object System.Drawing.RectangleF 13, 235, ($w - 26), 78
  Fill-Round $g $info 12 (C 180 8 11 20) (C 215 3 5 10) (C 55 255 218 104) 1
}

Save-Png 'enh_ritual_card_frame.png' 420 580 {
  param($g, $w, $h)
  $outer = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 16)
  $shadow = New-Object System.Drawing.SolidBrush (C 120 0 0 0)
  $g.FillPath($shadow, (RoundedPath 18 22 ($w - 36) ($h - 26) 42))
  $shadow.Dispose()

  $body = New-Object System.Drawing.Drawing2D.LinearGradientBrush $outer, (C 255 10 41 72), (C 255 4 8 24), 90
  $bodyBlend = New-Object System.Drawing.Drawing2D.ColorBlend
  $bodyBlend.Positions = @(0.0, 0.38, 0.7, 1.0)
  $bodyBlend.Colors = @((C 255 16 66 108), (C 255 7 27 62), (C 255 83 48 18), (C 255 14 6 3))
  $body.InterpolationColors = $bodyBlend
  $outerPath = RoundedPath $outer.X $outer.Y $outer.Width $outer.Height 42
  $g.FillPath($body, $outerPath)
  $body.Dispose()

  $gold1 = New-Object System.Drawing.Pen (C 255 255 231 131), 8
  $gold2 = New-Object System.Drawing.Pen (C 255 183 105 18), 4
  $cream = New-Object System.Drawing.Pen (C 220 255 255 226), 2
  $g.DrawPath($gold1, $outerPath)
  $g.DrawPath($gold2, (RoundedPath 20 20 ($w - 40) ($h - 40) 34))
  $g.DrawPath($cream, (RoundedPath 31 31 ($w - 62) ($h - 62) 28))
  $gold1.Dispose(); $gold2.Dispose(); $cream.Dispose()

  $art = New-Object System.Drawing.RectangleF 42, 44, ($w - 84), 330
  $artBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush $art, (C 88 255 255 255), (C 0 255 255 255), 90
  $g.FillPath($artBrush, (RoundedPath $art.X $art.Y $art.Width $art.Height 26))
  $artBrush.Dispose()

  $name = New-Object System.Drawing.RectangleF 42, 456, ($w - 84), 70
  Fill-Round $g $name 18 (C 225 7 18 38) (C 235 2 6 16) (C 95 255 225 130) 1

  $shine = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 0, 0, $w, 150), (C 130 255 255 255), (C 0 255 255 255), 90
  $g.FillPath($shine, (RoundedPath 24 18 ($w - 48) 130 36))
  $shine.Dispose()

  $linePen = New-Object System.Drawing.Pen (C 100 103 220 255), 2
  $g.DrawLine($linePen, 62, 410, ($w - 62), 410)
  $g.DrawLine($linePen, 72, 426, ($w - 72), 426)
  $linePen.Dispose()
}

Save-Png 'enh_ritual_meter_frame.png' 760 56 {
  param($g, $w, $h)
  $outer = New-Object System.Drawing.RectangleF 4, 4, ($w - 8), ($h - 8)
  Fill-Round $g $outer 24 (C 230 13 9 3) (C 230 1 1 1) (C 220 255 218 104) 3
  $inner = New-Object System.Drawing.RectangleF 17, 17, ($w - 34), ($h - 34)
  Fill-Round $g $inner 11 (C 155 255 255 255) (C 15 255 255 255) (C 45 255 255 255) 1
}

Save-Png 'enh_ritual_result_bar.png' 720 118 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 16)
  Fill-Round $g $rect 20 (C 216 17 33 49) (C 226 5 10 20) (C 125 255 255 255) 1
  Draw-Shine $g $rect 20
  $badge = New-Object System.Drawing.RectangleF ($w - 132), 20, 96, 78
  Fill-Round $g $badge 10 (C 245 255 255 255) (C 245 196 205 218) (C 160 255 255 255) 1
  $beam = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 18, 10, ($w - 36), ($h - 20)), (C 0 103 220 255), (C 100 103 220 255), 0
  $g.FillRectangle($beam, 20, 54, ($w - 190), 2)
  $beam.Dispose()
}

Save-Png 'upg_header_btn.png' 130 78 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 6, 6, ($w - 12), ($h - 14)
  Fill-Round $g $rect 18 (C 246 82 95 112) (C 246 23 34 52) (C 132 255 255 255) 1
  Draw-Shine $g $rect 18
  $edge = New-Object System.Drawing.Pen (C 82 255 218 104), 1
  $g.DrawPath($edge, (RoundedPath 13 13 ($w - 26) ($h - 30) 14))
  $edge.Dispose()
}

Save-Png 'upg_header_title.png' 460 78 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 34 255 218 104)
  $rect = New-Object System.Drawing.RectangleF 6, 6, ($w - 12), ($h - 14)
  Fill-Round $g $rect 18 (C 250 94 93 82) (C 250 35 42 46) (C 142 255 225 135) 1
  Draw-Shine $g $rect 18
  $line = New-Object System.Drawing.Pen (C 72 255 218 104), 2
  $g.DrawLine($line, 36, 54, ($w - 36), 54)
  $line.Dispose()
}

Save-Png 'upg_gold_badge.png' 260 78 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 6, 6, ($w - 12), ($h - 14)
  Fill-Round $g $rect 18 (C 246 75 77 74) (C 246 28 31 34) (C 128 255 255 255) 1
  Draw-Shine $g $rect 18
  $coin = New-Object System.Drawing.RectangleF 18, 17, 38, 38
  $coinPath = New-Object System.Drawing.Drawing2D.GraphicsPath
  $coinPath.AddEllipse($coin)
  $coinBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush $coin, (C 255 255 241 150), (C 255 219 131 20), 90
  $g.FillPath($coinBrush, $coinPath)
  $coinBrush.Dispose()
  $coinPen = New-Object System.Drawing.Pen (C 210 98 43 3), 2
  $g.DrawPath($coinPen, $coinPath)
  $coinPen.Dispose()
  $coinPath.Dispose()
}

Save-Png 'upg_card.png' 760 176 {
  param($g, $w, $h)
  $shadow = New-Object System.Drawing.RectangleF 12, 18, ($w - 24), ($h - 26)
  $shadowPath = RoundedPath $shadow.X $shadow.Y $shadow.Width $shadow.Height 24
  $shadowBrush = New-Object System.Drawing.SolidBrush (C 96 0 0 0)
  $g.FillPath($shadowBrush, $shadowPath)
  $shadowBrush.Dispose()
  $shadowPath.Dispose()
  $rect = New-Object System.Drawing.RectangleF 7, 7, ($w - 14), ($h - 22)
  Fill-Round $g $rect 24 (C 244 68 82 103) (C 244 20 29 43) (C 142 190 216 244) 1
  Draw-Shine $g $rect 24
  $line = New-Object System.Drawing.Pen (C 50 255 218 104), 2
  $g.DrawLine($line, 22, 120, ($w - 22), 120)
  $line.Dispose()
}

Save-Png 'upg_card_ready.png' 760 176 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 38 255 218 104)
  $rect = New-Object System.Drawing.RectangleF 7, 7, ($w - 14), ($h - 22)
  Fill-Round $g $rect 24 (C 248 79 91 107) (C 248 19 28 42) (C 215 255 218 104) 2
  Draw-Shine $g $rect 24
  $line = New-Object System.Drawing.Pen (C 92 255 218 104), 2
  $g.DrawLine($line, 22, 120, ($w - 22), 120)
  $line.Dispose()
}

Save-Png 'upg_card_max.png' 760 176 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 44 93 230 255)
  $rect = New-Object System.Drawing.RectangleF 7, 7, ($w - 14), ($h - 22)
  Fill-Round $g $rect 24 (C 248 86 97 106) (C 248 34 36 39) (C 210 255 225 135) 2
  Draw-Shine $g $rect 24
  $line = New-Object System.Drawing.Pen (C 100 255 238 164), 2
  $g.DrawLine($line, 22, 120, ($w - 22), 120)
  $line.Dispose()
}

Save-Png 'upg_buy_gold.png' 176 116 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 58 255 218 104)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 22)
  Fill-Round $g $rect 18 (C 255 255 242 165) (C 255 224 132 26) (C 235 255 255 255) 2
  Draw-Shine $g $rect 18
  $base = New-Object System.Drawing.RectangleF 28, ($h - 29), ($w - 56), 10
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $base, (C 112 116 49 2), (C 0 116 49 2), 0
  $g.FillRectangle($b, $base)
  $b.Dispose()
}

Save-Png 'upg_buy_disabled.png' 176 116 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 22)
  Fill-Round $g $rect 18 (C 190 81 91 105) (C 190 35 42 54) (C 62 255 255 255) 1
  Draw-Shine $g $rect 18
}

Save-Png 'upg_buy_max.png' 176 116 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 52 93 230 255)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 22)
  Fill-Round $g $rect 18 (C 255 109 232 255) (C 255 42 112 185) (C 220 255 255 255) 2
  Draw-Shine $g $rect 18
}

Save-Png 'upg_meter_track.png' 420 30 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 4, 7, ($w - 8), ($h - 14)
  Fill-Round $g $rect 8 (C 170 3 8 17) (C 170 18 25 35) (C 54 255 255 255) 1
}

function Draw-UpgIconFrame($g, $w, $h) {
  Draw-Glow $g $w $h (C 42 255 218 104)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 20)
  Fill-Round $g $rect 24 (C 246 63 76 96) (C 246 13 20 34) (C 156 255 218 104) 2
  Draw-Shine $g $rect 24
}

Save-Png 'upg_icon_castle_atk.png' 128 128 {
  param($g, $w, $h)
  Draw-UpgIconFrame $g $w $h
  $gold = New-Object System.Drawing.Pen (C 255 255 219 103), 4
  $red = New-Object System.Drawing.SolidBrush (C 255 223 45 55)
  $dark = New-Object System.Drawing.SolidBrush (C 255 83 17 20)
  $g.FillRectangle($red, 36, 48, 56, 42)
  $g.FillRectangle($dark, 46, 64, 14, 26)
  $g.FillRectangle($dark, 68, 64, 14, 26)
  $g.FillRectangle($red, 31, 38, 18, 52)
  $g.FillRectangle($red, 79, 38, 18, 52)
  $g.DrawRectangle($gold, 31, 38, 18, 52)
  $g.DrawRectangle($gold, 79, 38, 18, 52)
  $g.DrawRectangle($gold, 36, 48, 56, 42)
  $roof = New-Object System.Drawing.SolidBrush (C 255 255 86 96)
  $g.FillPolygon($roof, @((New-Object System.Drawing.Point 26,44),(New-Object System.Drawing.Point 40,28),(New-Object System.Drawing.Point 54,44)))
  $g.FillPolygon($roof, @((New-Object System.Drawing.Point 74,44),(New-Object System.Drawing.Point 88,28),(New-Object System.Drawing.Point 102,44)))
  $g.FillPolygon($roof, @((New-Object System.Drawing.Point 38,52),(New-Object System.Drawing.Point 64,30),(New-Object System.Drawing.Point 90,52)))
  $red.Dispose(); $dark.Dispose(); $gold.Dispose(); $roof.Dispose()
}

Save-Png 'upg_icon_castle_def.png' 128 128 {
  param($g, $w, $h)
  Draw-UpgIconFrame $g $w $h
  $path = New-Object System.Drawing.Drawing2D.GraphicsPath
  $path.AddPolygon(@(
    (New-Object System.Drawing.Point 64,25),
    (New-Object System.Drawing.Point 95,38),
    (New-Object System.Drawing.Point 90,72),
    (New-Object System.Drawing.Point 64,99),
    (New-Object System.Drawing.Point 38,72),
    (New-Object System.Drawing.Point 33,38)
  ))
  $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.RectangleF 32, 24, 64, 78), (C 255 120 226 255), (C 255 23 117 255), 90
  $g.FillPath($brush, $path)
  $pen = New-Object System.Drawing.Pen (C 255 236 250 255), 4
  $g.DrawPath($pen, $path)
  $line = New-Object System.Drawing.Pen (C 120 255 255 255), 3
  $g.DrawLine($line, 64, 30, 64, 92)
  $brush.Dispose(); $pen.Dispose(); $line.Dispose(); $path.Dispose()
}

Save-Png 'upg_icon_prod_rate.png' 128 128 {
  param($g, $w, $h)
  Draw-UpgIconFrame $g $w $h
  $tooth = New-Object System.Drawing.SolidBrush (C 255 214 204 235)
  for ($i = 0; $i -lt 8; $i++) {
    $a = ($i * [Math]::PI / 4)
    $x = 64 + [Math]::Cos($a) * 34
    $y = 64 + [Math]::Sin($a) * 34
    $g.FillEllipse($tooth, [float]($x - 9), [float]($y - 9), 18, 18)
  }
  $outer = New-Object System.Drawing.RectangleF 30, 30, 68, 68
  $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush $outer, (C 255 241 238 255), (C 255 125 111 170), 90
  $g.FillEllipse($brush, $outer)
  $pen = New-Object System.Drawing.Pen (C 255 70 62 98), 4
  $g.DrawEllipse($pen, $outer)
  $inner = New-Object System.Drawing.SolidBrush (C 255 38 46 64)
  $g.FillEllipse($inner, 50, 50, 28, 28)
  $tooth.Dispose(); $brush.Dispose(); $pen.Dispose(); $inner.Dispose()
}

Save-Png 'upg_icon_unit_atk.png' 128 128 {
  param($g, $w, $h)
  Draw-UpgIconFrame $g $w $h
  $blade = New-Object System.Drawing.Pen (C 255 224 232 245), 8
  $blade.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $blade.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $goldPen = New-Object System.Drawing.Pen (C 255 255 205 75), 5
  $goldPen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $goldPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $g.DrawLine($blade, 36, 34, 91, 89)
  $g.DrawLine($blade, 92, 34, 37, 89)
  $g.DrawLine($goldPen, 47, 78, 31, 94)
  $g.DrawLine($goldPen, 81, 78, 97, 94)
  $guard = New-Object System.Drawing.Pen (C 255 105 68 170), 5
  $g.DrawLine($guard, 47, 68, 60, 81)
  $g.DrawLine($guard, 81, 68, 68, 81)
  $blade.Dispose(); $goldPen.Dispose(); $guard.Dispose()
}

Save-Png 'upg_icon_unit_def.png' 128 128 {
  param($g, $w, $h)
  Draw-UpgIconFrame $g $w $h
  $body = New-Object System.Drawing.RectangleF 35, 52, 58, 44
  $armor = New-Object System.Drawing.Drawing2D.LinearGradientBrush $body, (C 255 226 232 242), (C 255 101 113 130), 90
  $g.FillPath($armor, (RoundedPath $body.X $body.Y $body.Width $body.Height 16))
  $pen = New-Object System.Drawing.Pen (C 255 58 68 82), 4
  $g.DrawPath($pen, (RoundedPath $body.X $body.Y $body.Width $body.Height 16))
  $helm = New-Object System.Drawing.Rectangle 41, 30, 46, 38
  $helmBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush $helm, (C 255 246 246 250), (C 255 132 143 160), 90
  $g.FillPie($helmBrush, 41, 30, 46, 38, 180, 180)
  $g.DrawArc($pen, 41, 30, 46, 38, 180, 180)
  $accent = New-Object System.Drawing.Pen (C 255 255 205 75), 4
  $g.DrawLine($accent, 64, 35, 64, 92)
  $armor.Dispose(); $pen.Dispose(); $helmBrush.Dispose(); $accent.Dispose()
}

Save-Png 'sx_panel.png' 760 620 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 45 255 213 92)
  $shadow = New-Object System.Drawing.RectangleF 24, 38, ($w - 48), ($h - 68)
  $shadowPath = RoundedPath $shadow.X $shadow.Y $shadow.Width $shadow.Height 34
  $shadowBrush = New-Object System.Drawing.SolidBrush (C 128 0 0 0)
  $g.FillPath($shadowBrush, $shadowPath)
  $shadowBrush.Dispose()
  $shadowPath.Dispose()

  $rect = New-Object System.Drawing.RectangleF 14, 18, ($w - 28), ($h - 52)
  Fill-Round $g $rect 32 (C 250 53 65 84) (C 250 10 17 30) (C 220 255 219 103) 3
  Draw-Shine $g $rect 32

  $inner = New-Object System.Drawing.RectangleF 32, 88, ($w - 64), ($h - 152)
  Fill-Round $g $inner 24 (C 176 12 21 36) (C 176 4 9 18) (C 86 177 210 245) 1

  $topLine = New-Object System.Drawing.Pen (C 112 255 226 134), 2
  $g.DrawLine($topLine, 60, 92, ($w - 60), 92)
  $g.DrawLine($topLine, 60, ($h - 84), ($w - 60), ($h - 84))
  $topLine.Dispose()
}

Save-Png 'sx_header_badge.png' 220 132 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 72 255 52 52)
  $rect = New-Object System.Drawing.RectangleF 18, 10, ($w - 36), ($h - 28)
  Fill-Round $g $rect 24 (C 255 221 38 35) (C 255 120 5 5) (C 238 255 232 156) 3
  Draw-Shine $g $rect 24
  $inner = New-Object System.Drawing.RectangleF 28, 21, ($w - 56), ($h - 50)
  $pen = New-Object System.Drawing.Pen (C 160 255 255 255), 2
  $g.DrawPath($pen, (RoundedPath $inner.X $inner.Y $inner.Width $inner.Height 18))
  $pen.Dispose()
}

Save-Png 'sx_title_plate.png' 520 86 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 34 255 218 104)
  $rect = New-Object System.Drawing.RectangleF 10, 10, ($w - 20), ($h - 24)
  Fill-Round $g $rect 22 (C 250 81 88 100) (C 250 24 31 45) (C 146 255 226 134) 2
  Draw-Shine $g $rect 22
  $line = New-Object System.Drawing.Pen (C 72 255 218 104), 2
  $g.DrawLine($line, 42, 54, ($w - 42), 54)
  $line.Dispose()
}

Save-Png 'sx_info_panel.png' 640 178 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 9, 8, ($w - 18), ($h - 20)
  Fill-Round $g $rect 24 (C 238 243 249 255) (C 238 195 215 238) (C 172 255 255 255) 2
  Draw-Shine $g $rect 24
  $bottom = New-Object System.Drawing.RectangleF 38, ($h - 38), ($w - 76), 7
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $bottom, (C 108 24 57 92), (C 0 24 57 92), 0
  $g.FillRectangle($b, $bottom)
  $b.Dispose()
}

Save-Png 'sx_btn_gold.png' 220 92 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 56 255 218 104)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 18)
  Fill-Round $g $rect 16 (C 255 255 241 156) (C 255 222 130 22) (C 238 255 255 255) 2
  Draw-Shine $g $rect 16
  $base = New-Object System.Drawing.RectangleF 26, ($h - 23), ($w - 52), 8
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $base, (C 120 116 49 2), (C 0 116 49 2), 0
  $g.FillRectangle($b, $base)
  $b.Dispose()
}

Save-Png 'sx_btn_red.png' 250 92 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 52 255 70 56)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 18)
  Fill-Round $g $rect 16 (C 255 224 42 38) (C 255 139 12 13) (C 226 255 224 155) 2
  Draw-Shine $g $rect 16
  $base = New-Object System.Drawing.RectangleF 30, ($h - 23), ($w - 60), 8
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $base, (C 124 79 3 4), (C 0 79 3 4), 0
  $g.FillRectangle($b, $base)
  $b.Dispose()
}

Save-Png 'sx_btn_dark.png' 640 86 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 18)
  Fill-Round $g $rect 18 (C 248 52 61 76) (C 248 8 14 25) (C 132 255 255 255) 1
  Draw-Shine $g $rect 18
  $line = New-Object System.Drawing.Pen (C 72 255 218 104), 1
  $g.DrawLine($line, 42, 58, ($w - 42), 58)
  $line.Dispose()
}

Save-Png 'sx_btn_disabled.png' 220 92 {
  param($g, $w, $h)
  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 18)
  Fill-Round $g $rect 16 (C 176 83 92 105) (C 176 37 44 56) (C 54 255 255 255) 1
  Draw-Shine $g $rect 16
}

Save-Png 'battle_retreat_btn.png' 260 104 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 54 255 80 64)
  $shadow = New-Object System.Drawing.RectangleF 14, 20, ($w - 28), ($h - 28)
  $shadowPath = RoundedPath $shadow.X $shadow.Y $shadow.Width $shadow.Height 24
  $shadowBrush = New-Object System.Drawing.SolidBrush (C 112 0 0 0)
  $g.FillPath($shadowBrush, $shadowPath)
  $shadowBrush.Dispose()
  $shadowPath.Dispose()

  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 20)
  Fill-Round $g $rect 22 (C 255 225 45 42) (C 255 123 11 12) (C 236 255 226 142) 2
  Draw-Shine $g $rect 22

  $inner = New-Object System.Drawing.RectangleF 16, 15, ($w - 32), ($h - 36)
  $pen = New-Object System.Drawing.Pen (C 96 255 255 255), 2
  $g.DrawPath($pen, (RoundedPath $inner.X $inner.Y $inner.Width $inner.Height 17))
  $pen.Dispose()

  $base = New-Object System.Drawing.RectangleF 34, ($h - 27), ($w - 68), 9
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $base, (C 124 76 3 4), (C 0 76 3 4), 0
  $g.FillRectangle($b, $base)
  $b.Dispose()
}

Save-Png 'stage_tutorial_btn.png' 640 92 {
  param($g, $w, $h)
  Draw-Glow $g $w $h (C 48 255 218 104)
  $shadow = New-Object System.Drawing.RectangleF 16, 18, ($w - 32), ($h - 28)
  $shadowPath = RoundedPath $shadow.X $shadow.Y $shadow.Width $shadow.Height 24
  $shadowBrush = New-Object System.Drawing.SolidBrush (C 118 0 0 0)
  $g.FillPath($shadowBrush, $shadowPath)
  $shadowBrush.Dispose()
  $shadowPath.Dispose()

  $rect = New-Object System.Drawing.RectangleF 8, 8, ($w - 16), ($h - 20)
  Fill-Round $g $rect 22 (C 252 70 82 101) (C 252 13 22 38) (C 196 255 218 104) 2
  Draw-Shine $g $rect 22

  $left = New-Object System.Drawing.RectangleF 24, 18, 60, 48
  Fill-Round $g $left 14 (C 245 255 241 156) (C 245 219 129 20) (C 205 255 255 255) 1
  $pen = New-Object System.Drawing.Pen (C 255 54 28 4), 4
  $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $g.DrawLine($pen, 47, 42, 59, 54)
  $g.DrawLine($pen, 59, 54, 74, 31)
  $pen.Dispose()

  $line = New-Object System.Drawing.Pen (C 72 255 218 104), 2
  $g.DrawLine($line, 104, 61, ($w - 42), 61)
  $line.Dispose()
}

Write-Host "enhance ui assets generated in $outDir"
