// SPDX-License-Identifier: MPL-2.0
#include "Arinc615aThaC.h"
#include "../workbench/EntryPoints.h"
#include <future>
#include <iostream>
#include <string>
#include <string_view>
#include <thread>

int main(int argc, char **argv)
{
  if (argc == 2 && std::string_view(argv[1]) == "--self-test") return arinc615aSelfTest();
  if (argc == 3 && std::string_view(argv[1]) == "--fixtures") return arinc615aWriteFixtures(argv[2]);
  // Host rehearsal of the board procedure in VXWORKS_TEST_PROCEDURE.md.
  if (argc == 3 && std::string_view(argv[1]) == "--prepare") return arinc615aPrepareTest(argv[2]);
  if (argc == 3 && std::string_view(argv[1]) == "--verify") return arinc615aVerifyTestUpload(argv[2]);
  if (argc != 2) { std::cerr << "Usage: arinc_host_runner config.json\n"; return 2; }
  auto result = std::async(std::launch::async, [&] { return arinc615a_tha_run_file(argv[1]); });
  std::string command;
  std::getline(std::cin, command);
  for (int attempt = 0; attempt < 100 && result.wait_for(std::chrono::milliseconds{0}) != std::future_status::ready; ++attempt) {
    arinc615a_tha_request_stop();
    std::this_thread::sleep_for(std::chrono::milliseconds{10});
  }
  return result.get();
}
