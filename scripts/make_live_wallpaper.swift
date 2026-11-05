// Live Photo pair for the iOS lock-screen wallpaper (04.11.2026). makelive wrote only the content identifier;
// Photos accepted the pair, the wallpaper picker did not list it. Real Live Photo movies also carry a timed metadata
// track "com.apple.quicktime.still-image-time" marking the still frame. This tool re-writes the movie with
// AVAssetWriter (content identifier + still-image-time track) and the JPEG with the same identifier in the
// Apple maker note (key 17). Usage: swift make_live_wallpaper.swift <in.mov> <in.jpg> <out folder> <still time s>
import AVFoundation
import Foundation
import ImageIO
import UniformTypeIdentifiers

let a = CommandLine.arguments
let inMov = URL(fileURLWithPath: a[1]), inJpg = URL(fileURLWithPath: a[2]), outDir = URL(fileURLWithPath: a[3])
let stillT = Double(a[4])!
let id = UUID().uuidString
let outMov = outDir.appendingPathComponent("IMG_LIVE.MOV"), outJpg = outDir.appendingPathComponent("IMG_LIVE.JPG")
try? FileManager.default.removeItem(at: outMov); try? FileManager.default.removeItem(at: outJpg)

// image
let src = CGImageSourceCreateWithURL(inJpg as CFURL, nil)!
let dst = CGImageDestinationCreateWithURL(outJpg as CFURL, UTType.jpeg.identifier as CFString, 1, nil)!
var props = (CGImageSourceCopyPropertiesAtIndex(src, 0, nil) as? [String: Any]) ?? [:]
props[kCGImagePropertyMakerAppleDictionary as String] = ["17": id]
props[kCGImageDestinationLossyCompressionQuality as String] = 0.95
CGImageDestinationAddImageFromSource(dst, src, 0, props as CFDictionary)
guard CGImageDestinationFinalize(dst) else { fatalError("jpeg write failed") }

// movie
let asset = AVURLAsset(url: inMov)
let sem = DispatchSemaphore(value: 0)
var track: AVAssetTrack!
Task { track = try! await asset.loadTracks(withMediaType: .video).first!; sem.signal() }
sem.wait()
let reader = try AVAssetReader(asset: asset)
let rout = AVAssetReaderTrackOutput(track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
reader.add(rout)
let writer = try AVAssetWriter(outputURL: outMov, fileType: .mov)
let ci = AVMutableMetadataItem()
ci.key = "com.apple.quicktime.content.identifier" as NSString; ci.keySpace = .quickTimeMetadata
ci.value = id as NSString; ci.dataType = "com.apple.metadata.datatype.UTF-8"
writer.metadata = [ci]
var size = CGSize.zero, fps: Float = 30
let sem2 = DispatchSemaphore(value: 0)
Task { size = try! await track.load(.naturalSize); fps = try! await track.load(.nominalFrameRate); sem2.signal() }
sem2.wait()
let vin = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.hevc, AVVideoWidthKey: Int(size.width), AVVideoHeightKey: Int(size.height),
    AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 12_000_000, AVVideoExpectedSourceFrameRateKey: Int(fps)]])
vin.expectsMediaDataInRealTime = false
writer.add(vin)
let spec: [String: Any] = [kCMMetadataFormatDescriptionMetadataSpecificationKey_Identifier as String: "mdta/com.apple.quicktime.still-image-time",
                           kCMMetadataFormatDescriptionMetadataSpecificationKey_DataType as String: "com.apple.metadata.datatype.int8"]
var desc: CMFormatDescription?
CMMetadataFormatDescriptionCreateWithMetadataSpecifications(allocator: kCFAllocatorDefault, metadataType: kCMMetadataFormatType_Boxed,
                                                            metadataSpecifications: [spec] as CFArray, formatDescriptionOut: &desc)
let min = AVAssetWriterInput(mediaType: .metadata, outputSettings: nil, sourceFormatHint: desc)
let adaptor = AVAssetWriterInputMetadataAdaptor(assetWriterInput: min)
writer.add(min)
reader.startReading(); writer.startWriting(); writer.startSession(atSourceTime: .zero)
let st = AVMutableMetadataItem()
st.key = "com.apple.quicktime.still-image-time" as NSString; st.keySpace = .quickTimeMetadata
st.value = 0 as NSNumber; st.dataType = "com.apple.metadata.datatype.int8"
let still = CMTime(seconds: stillT, preferredTimescale: 600)
adaptor.append(AVTimedMetadataGroup(items: [st], timeRange: CMTimeRange(start: still, duration: CMTime(value: 1, timescale: 30))))
min.markAsFinished()
var n = 0
while let sb = rout.copyNextSampleBuffer() {
    while !vin.isReadyForMoreMediaData { usleep(2000) }
    vin.append(sb); n += 1
}
vin.markAsFinished()
let sem3 = DispatchSemaphore(value: 0)
writer.finishWriting { sem3.signal() }
sem3.wait()
if writer.status != .completed { fatalError("movie write failed: \(String(describing: writer.error))") }
print("LIVE_PAIR_DONE id=\(id) frames=\(n) size=\(Int(size.width))x\(Int(size.height)) fps=\(fps) still=\(stillT)s")
