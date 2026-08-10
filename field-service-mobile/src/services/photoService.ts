import * as FileSystem from "expo-file-system/legacy";
import * as Crypto from "expo-crypto";
import { api } from "./api";
import type { LocalPhoto } from "../types";

export function guessMimeType(filename: string): string {
  const lower = filename.toLowerCase();
  if (lower.endsWith(".png")) return "image/png";
  if (lower.endsWith(".webp")) return "image/webp";
  return "image/jpeg";
}

export async function getPhotoMetadata(uri: string, filename: string) {
  const info = await FileSystem.getInfoAsync(uri);
  if (!info.exists) {
    throw new Error("Photo file not found on device.");
  }

  const base64 = await FileSystem.readAsStringAsync(uri, {
    encoding: FileSystem.EncodingType.Base64,
  });

  const sha256_checksum = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    base64,
    { encoding: Crypto.CryptoEncoding.BASE64 }
  );

  const fileSize =
    "size" in info && typeof info.size === "number" ? info.size : base64.length;

  return {
    mime_type: guessMimeType(filename),
    file_size_bytes: fileSize > 0 ? fileSize : 1,
    sha256_checksum,
  };
}

export async function uploadPhotoFile(
  reportServerId: string,
  photo: LocalPhoto
): Promise<void> {
  const form = new FormData();
  form.append("client_photo_id", photo.client_id);
  form.append("file", {
    uri: photo.local_uri,
    name: photo.original_filename,
    type: photo.mime_type,
  } as unknown as Blob);

  await api.post(`/reports/${reportServerId}/photos`, form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60_000,
  });
}
