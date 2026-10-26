// 筋トレメモのスクショを macOS 内蔵の Vision フレームワークで OCR する。
// 画像はMacの外に送られない (ネット接続も不要)。
//
// 使い方:
//   swiftc -O kintorememo/ocr.swift -o kintorememo/ocr   # 初回だけコンパイル
//   kintorememo/ocr raw/kintorememo/bench/*.(png|PNG) > ocr_bench.tsv   # iPhoneのスクショは拡張子が大文字のことがある
//
// 出力 (1行1テキスト、タブ区切り):
//   ### <画像パス>            ← 画像の区切り
//   <y> <x> <テキスト>        ← y,x は画像内の位置 (0〜1、左上が原点)。行の組み立ては km_parse.py が行う
//   <y> -1  CHECK             ← 補助欄の赤いレ点を検出した位置
import AppKit
import Foundation
import Vision

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("読めない: \(path)\n".data(using: .utf8)!)
        continue
    }

    // 1. 文字認識
    //    .accurate: 速度より精度を優先するモード
    //    日本語と英語を指定 (日付・kg・回・メモが混在するため)
    //    言語補正はオフ: 「65.0kg」などの数字が辞書の単語に置き換えられるのを防ぐ
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["ja-JP", "en-US"]
    req.usesLanguageCorrection = false
    try VNImageRequestHandler(cgImage: cg).perform([req])

    print("### \(path)")
    for o in req.results ?? [] {
        guard let t = o.topCandidates(1).first?.string else { continue }
        // Vision の座標は左下原点なので、y を上下反転して上原点にそろえる
        let b = o.boundingBox
        print(String(format: "%.4f\t%.4f\t", 1 - b.midY, b.minX) + t)
    }

    // 2. 補助チェックの検出
    //    補助欄の赤いレ点は文字ではないので OCR では読めない。画素の色で判定する。
    //    上から1ピクセル行ずつ見て、補助欄 (横位置 78〜83%) に赤い画素があり、
    //    かつ画面中央 (50%) は赤くない行を「レ点」とみなす。
    //    中央も赤い行は日付見出しの赤い帯なので除外する。
    let rep = NSBitmapImageRep(cgImage: cg)
    func red(_ x: Int, _ y: Int) -> Bool {
        guard let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.deviceRGB) else { return false }
        return c.redComponent > 0.7 && c.greenComponent < 0.4 && c.blueComponent < 0.4
    }
    let w = rep.pixelsWide, h = rep.pixelsHigh
    var start = -1
    for y in 0..<h {
        let hit = (Int(0.78 * Double(w))...Int(0.83 * Double(w))).contains { red($0, y) } && !red(w / 2, y)
        if hit && start < 0 { start = y }
        if !hit && start >= 0 {
            // 10ピクセル以上続いた赤い範囲だけ採用 (ノイズ除け)。中心の y を出力
            if y - start > 10 { print(String(format: "%.4f\t-1\tCHECK", Double(start + y) / 2 / Double(h))) }
            start = -1
        }
    }
}
