//
// Created by Juncheng Yang on 5/9/21.
//

#include <filesystem>

#include "../cli_reader_utils.h"
#include "internal.h"
#include "traceAnalyzer/analyzer.h"

using namespace traceAnalyzer;

int main(int argc, char *argv[]) {
  struct arguments args;
  parse_cmd(argc, argv, &args);

  /* create output directory before constructing TraceAnalyzer so that
   * ReuseDistribution::turn_on_stream_dump() can open stream files */
  {
    std::filesystem::path out(args.ofilepath);
    if (out.has_parent_path()) {
      std::filesystem::create_directories(out.parent_path());
    }
  }

  TraceAnalyzer *stat = new TraceAnalyzer(
      args.reader, args.ofilepath, args.analysis_option, args.analysis_param);
  stat->run();

  std::filesystem::create_directories("analysis");
  ofstream ofs("analysis/traceStat", ios::out | ios::app);
  ofs << *stat << endl;
  ofs.close();
  cout << *stat;

  delete stat;

  close_reader(args.reader);

  return 0;
}
