#!/bin/bash

# Define variables
DATA_DIR="./data"
OUTPUT_DIR="./results"
ALGORITHMS=run
PARAMS=("0.01" "0.1")
CPU_LOG="cpu_usage.log"
MEMORY_LOG="memory_usage.log"
DEBUG_MODE=true  # Set to true to enable debug output

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Clear CPU usage log
> "$CPU_LOG"

# Iterate over all .zst files in the subdirectories of the data directory
find "$DATA_DIR" -mindepth 2 -type f -name "*.zst" | sort | while read -r zst_file; do
  # Extract file and directory names
  trace_name=$(basename "$zst_file")
  trace_dir=$(dirname "$zst_file")

  # Create a directory for the current trace
  trace_output_dir="$OUTPUT_DIR/$trace_name"
  mkdir -p "$trace_output_dir"

  # Initialize output files with headers
  if [ ! -f "$trace_output_dir/performance.txt" ]; then
    echo "# Algorithm Parameter MissRatio ByteMissRatio Throughput(MQPS)" > "$trace_output_dir/performance.txt"
  fi
  if [ ! -f "$trace_output_dir/CPU.txt" ]; then
    echo "# Algorithm Parameter ElapsedTime(s) AvgCPU_Monitor(%) MaxCPU_Monitor(%) CumulativeCPU_Monitor(%*s)" > "$trace_output_dir/CPU.txt"
  fi
  if [ ! -f "$trace_output_dir/memory.txt" ]; then
    echo "# Algorithm Parameter AvgMemory_Monitor(KB) PeakMemory_Monitor(KB)" > "$trace_output_dir/memory.txt"
  fi

  # Iterate over all algorithms
  for algo in "${ALGORITHMS[@]}"; do
    # Iterate over all parameters
    for param in "${PARAMS[@]}"; do
      # Define output file
      output_file="$trace_output_dir/${algo}_${param}.log"
      error_log="$trace_output_dir/error_${algo}_${param}.log"

      # Print current execution info
      echo "Running: $trace_name with $algo and param $param"

      # Run cachesim directly to get its PID for reliable monitoring.
      # stdout -> output_file, stderr -> error_log
      ./_build/bin/cachesim "$zst_file" oracleGeneral "$algo" "$param" > "$output_file" 2> "$error_log" &
      # We can't just use $! because cachesim might be a wrapper script.
      # Instead, we find the PID by looking for the process running that specific zst file.
      # This is more robust. We give it a moment to start up.
      sleep 0.1
      cachesim_pid=$(pgrep -f "_build/bin/cachesim.*$zst_file" | head -n 1)

      # If PID is not found, wait a bit longer and try again.
      if [ -z "$cachesim_pid" ]; then
          sleep 0.5
          cachesim_pid=$(pgrep -f "_build/bin/cachesim.*$zst_file" | head -n 1)
      fi

      # If PID is still not found, log an error and skip.
      if [ -z "$cachesim_pid" ]; then
          echo "Error: Could not find PID for cachesim on $zst_file. Skipping." | tee -a "$error_log"
          continue
      fi

      # Print the PID to the terminal for verification
      echo "Monitoring PID: $cachesim_pid for $trace_name"

      # Monitor CPU and memory usage
      cpu_monitor_log="$trace_output_dir/cpu_monitor_${algo}_${param}.log"
      memory_monitor_log="$trace_output_dir/memory_monitor_${algo}_${param}.log"

      # Start monitoring CPU and memory usage in background after cachesim starts
      (
        echo "# Time(s) CPU(%) Memory(KB)" > "$cpu_monitor_log"
        echo "# Time(s) Memory(KB)" > "$memory_monitor_log"
        start_time=$(date +%s.%N)

        # Wait a very short time, just enough for the process to appear
        sleep 0.05

        # We monitor the PID we found, not the initial one.
        while [ -n "$cachesim_pid" ] && ps -p "$cachesim_pid" > /dev/null;
        do
          current_time=$(date +%s.%N)
          elapsed=$(echo "$current_time - $start_time" | bc -l)

          # Get all PIDs in the process tree for cachesim to capture all child processes.
          # pgrep -P gets all children of the parent PID.
          child_pids=$(pgrep -P "$cachesim_pid")

          # Combine parent and child PIDs into a bash array
          pids_to_monitor=("$cachesim_pid")
          if [ -n "$child_pids" ]; then
              # Append child PIDs to the array
              read -r -a child_pids_array <<< "$child_pids"
              pids_to_monitor+=("${child_pids_array[@]}")
          fi

          # Create a clean, comma-separated list for ps. Using printf is robust.
          all_pids_comma=$(printf ",%s" "${pids_to_monitor[@]}")
          all_pids_comma=${all_pids_comma:1} # Remove leading comma

          ps_output=""
          if [ -n "$all_pids_comma" ]; then
              # Use ps to get info for all PIDs. It's fast and reliable.
              # comm: command name, pid: process id, %cpu: cpu usage, rss: resident set size in KB
              ps_output=$(ps -p "$all_pids_comma" -o comm,pid,%cpu,rss --no-headers 2>/dev/null)
          fi

          # Debug: Log the raw ps output
          if [ "$DEBUG_MODE" = true ]; then
            echo "--- ps Output (Time: $elapsed, PIDs: $all_pids_comma) ---" >> "$trace_output_dir/ps_debug.log"
            echo "Found cachesim PID: $cachesim_pid" >> "$trace_output_dir/ps_debug.log"
            echo "ps command: ps -p \"$all_pids_comma\" -o comm,pid,%cpu,rss --no-headers" >> "$trace_output_dir/ps_debug.log"
            echo "$ps_output" >> "$trace_output_dir/ps_debug.log"
            echo "--- End ps Output ---" >> "$trace_output_dir/ps_debug.log"
          fi

          if [ -n "$ps_output" ]; then
            # Sum CPU and Memory for all processes in the tree
            # ps output is: comm,pid,%cpu,rss. We sum column 3 (%cpu) and 4 (rss).
            cpu_usage=$(echo "$ps_output" | awk '{sum+=$3} END {print sum}')
            memory_usage=$(echo "$ps_output" | awk '{sum+=$4} END {print sum}') # rss is in KB
          else
            # Process might have ended between ps check and ps command
            cpu_usage="0"
            memory_usage="0"
          fi

          if [ -n "$cpu_usage" ] && [ -n "$memory_usage" ]; then
            echo "$elapsed $cpu_usage $memory_usage" >> "$cpu_monitor_log"
            echo "$elapsed $memory_usage" >> "$memory_monitor_log"
          fi

          sleep 0.2
        done
      ) &
      monitor_pid=$!

      # Wait for cachesim to complete. We wait on the PID we found.
      if [ -n "$cachesim_pid" ]; then
        wait "$cachesim_pid"
      fi

      # Stop monitoring
      kill $monitor_pid 2>/dev/null

      # --- Data Extraction and Logging ---

      # Initialize variables to ensure they are always set
      miss_ratio="N/A"; byte_miss_ratio="N/A"; throughput="N/A"
      elapsed_time="N/A";
      avg_cpu="N/A"; max_cpu="N/A"; cumulative_cpu="N/A"
      avg_memory="N/A"; peak_memory="N/A"

      # Extract performance metrics from cachesim output
      if [ -f "$output_file" ]; then
        last_line=$(tail -n 1 "$output_file")
        if [[ "$last_line" == *"miss ratio"* ]] && [[ "$last_line" == *"MQPS"* ]]; then
          miss_ratio=$(echo "$last_line" | sed -n 's/.*, miss ratio \([0-9.]*\),.*/\1/p')
          byte_miss_ratio=$(echo "$last_line" | sed -n 's/.*byte miss ratio \([0-9.]*\).*/\1/p')
          throughput=$(echo "$last_line" | sed -n 's/.*throughput \([0-9.]*\) MQPS.*/\1/p')
        fi
      fi

      # Calculate monitored stats
      if [ -f "$cpu_monitor_log" ] && [ $(wc -l < "$cpu_monitor_log") -gt 1 ]; then
          # Get elapsed time from the last entry in the log
          elapsed_time=$(tail -n 1 "$cpu_monitor_log" | awk '{print $1}')
          # If elapsed_time is empty (e.g., file has only header), set to 0
          elapsed_time=${elapsed_time:-0}

          stats=$(tail -n +2 "$cpu_monitor_log" | awk '{sum+=$2; count++; if($2>max) max=$2; sum_cumulative+=$2*0.2} END {if(count>0) printf "%.2f %.2f %.2f", sum/count, max, sum_cumulative; else print "0 0 0"}')
          avg_cpu=$(echo "$stats" | awk '{print $1}')
          max_cpu=$(echo "$stats" | awk '{print $2}')
          cumulative_cpu=$(echo "$stats" | awk '{print $3}')
      fi

      if [ -f "$memory_monitor_log" ] && [ $(wc -l < "$memory_monitor_log") -gt 1 ]; then
          mem_stats=$(tail -n +2 "$memory_monitor_log" | awk '{sum+=$2; count++; if($2>max) max=$2} END {if(count>0) printf "%.0f %.0f", sum/count, max; else print "0 0"}')
          avg_memory=$(echo "$mem_stats" | awk '{print $1}')
          peak_memory=$(echo "$mem_stats" | awk '{print $2}')
      fi

      # Prepare output lines
      perf_line="$algo $param $miss_ratio $byte_miss_ratio $throughput"
      cpu_line="$algo $param $elapsed_time $avg_cpu $max_cpu $cumulative_cpu"
      mem_line="$algo $param $avg_memory $peak_memory"

      # Write to files
      echo "$perf_line" >> "$trace_output_dir/performance.txt"
      echo "$cpu_line" >> "$trace_output_dir/CPU.txt"
      echo "$mem_line" >> "$trace_output_dir/memory.txt"

      # Print combined results to terminal
      echo "---"
      echo "Result for $trace_name / $algo / $param:"
      echo "  Performance: $perf_line"
      echo "  CPU Usage:   $cpu_line"
      echo "  Memory Usage: $mem_line"
      echo "---"

      echo "Finished: $trace_name with $algo and param $param"
    done
  done

done

echo "All simulations completed. Results saved to $OUTPUT_DIR"
