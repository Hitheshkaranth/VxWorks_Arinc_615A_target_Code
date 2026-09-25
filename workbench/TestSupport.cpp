// SPDX-License-Identifier: MPL-2.0
// On-target test fixtures for the Windows-driven acceptance procedure
// (tests/vxworks_target_test.py). Everything is created on the target itself,
// so no host-to-board file copy is needed before a test run.
#include "EntryPoints.h"
#include <arinc_665/files/LoadHeaderFile.hpp>
#include <arinc_checksum/Arinc645Crc.hpp>
#include <cstdio>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>

namespace {

// Must match expected_payload() in tests/vxworks_target_test.py.
ArincSupport::RawData testPayload()
{
  ArincSupport::RawData payload(4097);
  for (std::size_t i = 0; i < payload.size(); ++i) payload[i] = std::byte(i % 251);
  return payload;
}

bool writeFile(const std::filesystem::path &path, const ArincSupport::RawData &data)
{
  std::ofstream file{path, std::ios::binary | std::ios::trunc};
  file.write(reinterpret_cast<const char *>(data.data()), static_cast<std::streamsize>(data.size()));
  return static_cast<bool>(file);
}

ArincSupport::RawData readFile(const std::filesystem::path &path)
{
  std::ifstream file{path, std::ios::binary};
  const std::string text{std::istreambuf_iterator<char>{file}, std::istreambuf_iterator<char>{}};
  ArincSupport::RawData data(text.size());
  for (std::size_t i = 0; i < text.size(); ++i) data[i] = std::byte(static_cast<unsigned char>(text[i]));
  return data;
}

}

extern "C" int arinc615aWriteFixtures(const char *directory)
{
  try {
    const std::filesystem::path dir{directory};
    std::filesystem::create_directories(dir);
    const auto payload = testPayload();
    ArincChecksum::Arinc645Crc16 crc;
    crc.process_bytes(payload.data(), payload.size());
    Arinc665::Files::LoadHeaderFile header;
    header.partNumber("DEMO-PN");
    header.dataFiles().push_back({"payload.bin", "DEMO-PN", payload.size(), crc.checksum(), {}});
    const auto valid = static_cast<ArincSupport::RawData>(header);
    header.dataFiles().clear();
    const auto empty = static_cast<ArincSupport::RawData>(header);
    header.dataFiles().push_back({"../escape.bin", "DEMO-PN", payload.size(), crc.checksum(), {}});
    const auto traversal = static_cast<ArincSupport::RawData>(header);
    if (!writeFile(dir / "demo.LUH", valid) || !writeFile(dir / "payload.bin", payload)
        || !writeFile(dir / "empty.LUH", empty) || !writeFile(dir / "traversal.LUH", traversal)) {
      std::printf("ARINC fixtures: cannot write into %s\n", directory);
      return 2;
    }
    return 0;
  } catch (const std::exception &error) {
    std::printf("ARINC fixtures failed: %s\n", error.what());
    return 1;
  } catch (...) { return 1; }
}

extern "C" int arinc615aPrepareTest(const char *root_directory)
{
  if (root_directory == nullptr || *root_directory == '\0') {
    std::puts("Usage: arinc615aPrepareTest \"/ram0/arinc\"");
    return 1;
  }
  try {
    const std::filesystem::path root{root_directory};
    const auto upload = root / "upload";
    const auto download = root / "download";
    std::filesystem::remove_all(upload);
    std::filesystem::remove(root / "escape.bin");
    std::filesystem::create_directories(upload);
    if (const int result = arinc615aWriteFixtures(download.string().c_str()); result != 0) return result;

    // Same schema as target-config.json. A 1 s TFTP timeout lets the host's
    // lost-packet test observe a retransmission well inside its wait window.
    const auto config = root / "test-config.json";
    std::ofstream file{config, std::ios::trunc};
    file << "{\n"
      "  \"version\": \"Arinc615a34\",\n"
      "  \"status_transmission_rate\": 1,\n"
      "  \"arinc_615a\": {\"local_tftp_address\": \"0.0.0.0\", \"dlp_retries\": 2,\n"
      "    \"tftp\": {\"port\": 59, \"timeout\": 1, \"retries\": 3}, \"protocol_file_logging\": false},\n"
      "  \"arinc_615a_find\": {\"local_find_address\": \"0.0.0.0\", \"find_port\": 1001},\n"
      "  \"find_information\": [{\"thwId\": \"ARINC\", \"thwTypeName\": \"THA\", \"thwPosition\": \"1\",\n"
      "    \"literalName\": \"ARINC 615A Test\", \"manufacturerCode\": \"UVDR\"}],\n"
      "  \"targets_configuration\": [{\n"
      "    \"target_id\": \"ARINC_1\",\n"
      "    \"information_operation\": {\"enabled\": true, \"targets_hardware\": {\"target_hardware\": {\n"
      "      \"literal_name\": \"ARINC 615A Test\", \"serial_number\": \"TEST001\",\n"
      "      \"part_numbers\": [{\"part_number\": \"DEMO-PN\", \"amendment\": \"\", \"part_designation\": \"Test payload\"}]}}},\n"
      "    \"upload_operation\": {\"enabled\": true, \"directory\": \"" << upload.generic_string() << "\", \"checksum_option\": false},\n"
      "    \"media_defined_download_operation\": {\"enabled\": true, \"directories\": {\"directory\": \"" << download.generic_string() << "\"}},\n"
      "    \"operator_defined_download_operation\": {\"enabled\": true, \"directories\": {\"directory\": \"" << download.generic_string() << "\"}}\n"
      "  }]\n"
      "}\n";
    if (!file) {
      std::printf("ARINC test: cannot write %s\n", config.generic_string().c_str());
      return 2;
    }
    std::printf("ARINC test prepared. Start the loader with config %s\n", config.generic_string().c_str());
    return 0;
  } catch (const std::exception &error) {
    std::printf("ARINC test preparation failed: %s\n", error.what());
    return 3;
  } catch (...) { return 3; }
}

extern "C" int arinc615aVerifyTestUpload(const char *root_directory)
{
  if (root_directory == nullptr || *root_directory == '\0') return 1;
  try {
    const std::filesystem::path root{root_directory};
    const auto uploaded = root / "upload" / "payload.bin";
    if (!std::filesystem::exists(uploaded)) {
      std::puts("ARINC upload check FAIL: upload/payload.bin missing");
      return 2;
    }
    if (readFile(uploaded) != testPayload()) {
      std::puts("ARINC upload check FAIL: upload/payload.bin differs from the reference payload");
      return 3;
    }
    if (std::filesystem::exists(root / "escape.bin")) {
      std::puts("ARINC upload check FAIL: path-traversal file escape.bin was written");
      return 4;
    }
    std::puts("ARINC upload check PASS (payload byte-identical, no path-traversal file)");
    return 0;
  } catch (const std::exception &error) {
    std::printf("ARINC upload check failed: %s\n", error.what());
    return 5;
  } catch (...) { return 5; }
}
