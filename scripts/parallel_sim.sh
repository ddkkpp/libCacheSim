#!/bin/bash

# Parallel simulation script for libCacheSim
# Runs multiple algorithms and cache sizes in parallel, monitoring performance

# Define variables
DATA_DIR="./data"
OUTPUT_DIR="./results/parallel"
CPU_LOG="cpu_usage_parallel.log"
MEMORY_LOG="memory_usage_parallel.log"
DEBUG_MODE=true  # Set to true to enable debug output

# Default values (can be overridden by command line arguments)
DEFAULT_TRACE_FORMAT="oracleGeneral"
DEFAULT_ALGOS="LRU,LHD,GDSF,ARC,SIEVE,S3FIFO,wtinylfu,lecar,cacheus,lrb,glcache,3lcache"
DEFAULT_PARAMS="0.001,0.1"
DEFAULT_MAX_PARALLEL=10  # Maximum number of simulations to run in parallel

# Debug mode - set to true to run a single test in foreground first
DEBUG_RUN_SINGLE=false    # Set to true to run one test in foreground first

# Parse command line arguments
TRACE_FORMAT="${1:-$DEFAULT_TRACE_FORMAT}"
ALGORITHMS="${2:-$DEFAULT_ALGOS}"
PARAMS="${3:-$DEFAULT_PARAMS}"
MAX_PARALLEL="${4:-$DEFAULT_MAX_PARALLEL}"
MEMORY_LIMIT="${5:-50}"  # Default to 75% memory usage limit

# Convert comma-separated lists to arrays
IFS=',' read -ra ALGO_ARRAY <<< "$ALGORITHMS"
IFS=',' read -ra PARAM_ARRAY <<< "$PARAMS"

# Create output directories
mkdir -p "$OUTPUT_DIR"

# Clear CPU usage log
> "$CPU_LOG"

echo "Starting parallel simulations for all trace files"
echo "Algorithms: ${ALGO_ARRAY[@]}"
echo "Parameters: ${PARAM_ARRAY[@]}"
echo "Max parallel jobs: $MAX_PARALLEL"
echo "Memory usage limit: $MEMORY_LIMIT%"

# Create an array to store background job PIDs
declare -a job_pids

# Function to run a single simulation
run_simulation() {
    local trace=$1
    local trace_format=$2
    local algo=$3
    local param=$4
    local output_dir=$5

    # Define output file
    local output_file="$output_dir/${algo}_${param}.log"
    local error_log="$output_dir/error_${algo}_${param}.log"

    # Print current execution info
    echo "Running: $trace with $algo and param $param"

    # Build the command with proper quoting
    local cmd="./_build/bin/cachesim \"$trace\" \"$trace_format\" \"$algo\" \"$param\""

    # Get current system memory usage
    local current_mem_usage=$(get_system_memory_usage)

    echo "Starting cachesim: $cmd (System memory: ${current_mem_usage}%)"

    # Debug logging
    if [ "$DEBUG_MODE" = true ]; then
        echo "Command: $cmd" >> "$output_dir/command_log.txt"
        echo "Output file: $output_file" >> "$output_dir/command_log.txt"
        echo "Error log: $error_log" >> "$output_dir/command_log.txt"
        echo "System memory before launch: ${current_mem_usage}%" >> "$output_dir/command_log.txt"
    fi

    # Execute the command directly using bash -c to handle arguments properly
    bash -c "./_build/bin/cachesim \"$trace\" \"$trace_format\" \"$algo\" \"$param\" > \"$output_file\" 2> \"$error_log\"" &

    # Get the PID directly from the background job
    local sim_pid=$!

    # 更新最后一个进程启动的时间戳（全局变量）
    last_process_start_time=$(date +%s)
    echo "$(date): Process started, updating timestamp. Next process can start after $(date -d @$((last_process_start_time + 300)))"

    # Add a small sleep to make sure the process has started before we check its status
    sleep 0.1

    # Verify process exists
    if ! ps -p $sim_pid > /dev/null; then
        echo "ERROR: cachesim process $sim_pid failed to start for $algo with param $param!" | tee -a "$error_log" "$output_dir/warnings.log"
        # Check error log
        if [ -s "$error_log" ]; then
            echo "Error log contents:" | tee -a "$output_dir/warnings.log"
            cat "$error_log" | tee -a "$output_dir/warnings.log"
        fi
    else
        echo "Cachesim process $sim_pid started successfully for $algo with param $param"
    fi

    # We need to wait a moment for the process to start
    sleep 0.1

    # Try to find the specific process with the most specific criteria first (algo + param + trace)
    local cachesim_pid=$(pgrep -f "_build/bin/cachesim.*$trace.*$algo.*$param" | head -n 1)

    # If not found, try with just algorithm and trace
    if [ -z "$cachesim_pid" ]; then
        sleep 0.2
        cachesim_pid=$(pgrep -f "_build/bin/cachesim.*$trace.*$algo" | head -n 1)
    fi

    # If still not found, try with just trace
    if [ -z "$cachesim_pid" ]; then
        sleep 0.2
        cachesim_pid=$(pgrep -f "_build/bin/cachesim.*$trace" | head -n 1)
    fi

    # If still not found, use the PID we captured at launch time
    if [ -z "$cachesim_pid" ]; then
        cachesim_pid=$sim_pid
        echo "Using launch PID $sim_pid for $algo with param $param"
    fi

    # If PID is still not found, log an error and skip.
    if [ -z "$cachesim_pid" ]; then
        echo "Error: Could not find PID for cachesim on $trace. Skipping." | tee -a "$error_log"
        return 1
    fi

    # Print the PID to the terminal for verification and check what we're actually monitoring
    echo "Monitoring PID: $cachesim_pid for $algo with param $param"

    # Double check what this PID is actually running
    local pid_cmd=$(ps -p "$cachesim_pid" -o cmd= 2>/dev/null)
    echo "  PID $cachesim_pid is running: $pid_cmd" | tee -a "$output_dir/pid_verification.log"

    # Monitor CPU and memory usage
    local cpu_monitor_log="$output_dir/cpu_monitor_${algo}_${param}.log"
    local memory_monitor_log="$output_dir/memory_monitor_${algo}_${param}.log"

    # Start monitoring CPU and memory usage in background
    (
        echo "# Time(s) CPU(%) Memory(KB)" > "$cpu_monitor_log"
        echo "# Time(s) Memory(KB)" > "$memory_monitor_log"
        local start_time=$(date +%s.%N)

        # Wait a very short time for the process to appear
        sleep 0.05

        # Monitor the process and its children
        while [ -n "$cachesim_pid" ] && ps -p "$cachesim_pid" > /dev/null; do
            local current_time=$(date +%s.%N)
            local elapsed=$(echo "$current_time - $start_time" | bc -l)

            # Get all PIDs in the process tree for cachesim
            local child_pids=$(pgrep -P "$cachesim_pid")

            # Combine parent and child PIDs
            local pids_to_monitor=("$cachesim_pid")
            if [ -n "$child_pids" ]; then
                read -r -a child_pids_array <<< "$child_pids"
                pids_to_monitor+=("${child_pids_array[@]}")
            fi

            # Create comma-separated list for ps
            local all_pids_comma=$(printf ",%s" "${pids_to_monitor[@]}")
            all_pids_comma=${all_pids_comma:1} # Remove leading comma

            local ps_output=""
            if [ -n "$all_pids_comma" ]; then
                ps_output=$(ps -p "$all_pids_comma" -o comm,pid,%cpu,rss --no-headers 2>/dev/null)
            fi

            # Debug logging
            if [ "$DEBUG_MODE" = true ]; then
                echo "--- ps Output (Time: $elapsed, PIDs: $all_pids_comma) ---" >> "$output_dir/ps_debug_${algo}_${param}.log"
                echo "$ps_output" >> "$output_dir/ps_debug_${algo}_${param}.log"
                echo "--- End ps Output ---" >> "$output_dir/ps_debug_${algo}_${param}.log"
            fi

            if [ -n "$ps_output" ]; then
                # Sum CPU and Memory for all processes in the tree
                local cpu_usage=$(echo "$ps_output" | awk '{sum+=$3} END {print sum}')
                local memory_usage=$(echo "$ps_output" | awk '{sum+=$4} END {print sum}') # rss is in KB

                # Validate the values
                if [[ ! "$cpu_usage" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
                    # Not a valid number, reset to 0
                    cpu_usage="0"
                fi
                if [[ ! "$memory_usage" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
                    # Not a valid number, reset to 0
                    memory_usage="0"
                fi
            else
                # Process might have ended
                local cpu_usage="0"
                local memory_usage="0"
            fi

            # Always write to logs, even if values are 0
            echo "$elapsed $cpu_usage $memory_usage" >> "$cpu_monitor_log"
            echo "$elapsed $memory_usage" >> "$memory_monitor_log"

            if [ "$DEBUG_MODE" = true ]; then
                echo "$(date +%H:%M:%S.%N) - $elapsed s: CPU=$cpu_usage%, MEM=$memory_usage KB" >> "$output_dir/monitor_debug_${algo}_${param}.log"
            fi

            sleep 0.2
        done
    ) &
    local monitor_pid=$!

    # Wait for cachesim to complete
    if [ -n "$cachesim_pid" ]; then
        wait "$cachesim_pid" 2>/dev/null
    fi

    # Stop monitoring
    kill $monitor_pid 2>/dev/null

    # Process and extract metrics
    process_results "$algo" "$param" "$output_file" "$cpu_monitor_log" "$memory_monitor_log" "$output_dir"

    echo "Finished: $algo with param $param"
}

# Function to process results and extract metrics
process_results() {
    local algo=$1
    local param=$2
    local output_file=$3
    local cpu_monitor_log=$4
    local memory_monitor_log=$5
    local output_dir=$6

    # Initialize variables
    local miss_ratio="N/A"; local byte_miss_ratio="N/A"; local throughput="N/A"
    local elapsed_time="N/A";
    local avg_cpu="N/A"; local max_cpu="N/A"; local cumulative_cpu="N/A"
    local avg_memory="N/A"; local peak_memory="N/A"

    # Extract performance metrics from cachesim output
    if [ -f "$output_file" ]; then
        # Check if file is empty
        if [ ! -s "$output_file" ]; then
            echo "Warning: Output file for $algo/$param is empty!" | tee -a "$output_dir/warnings.log"
        fi

        # Print some debug info
        echo "Debug: Output file content for $algo/$param:" >> "$output_dir/debug.log"
        cat "$output_file" >> "$output_dir/debug.log"
        echo "End of output file" >> "$output_dir/debug.log"

        # Get the last line and extract metrics
        local last_line=$(tail -n 1 "$output_file")
        if [[ "$last_line" == *"miss ratio"* ]]; then
            miss_ratio=$(echo "$last_line" | sed -n 's/.*, miss ratio \([0-9.]*\),.*/\1/p')
            byte_miss_ratio=$(echo "$last_line" | sed -n 's/.*byte miss ratio \([0-9.]*\).*/\1/p')

            # Extract throughput if available
            if [[ "$last_line" == *"throughput"* ]]; then
                throughput=$(echo "$last_line" | sed -n 's/.*throughput \([0-9.]*\) MQPS.*/\1/p')
            fi

            if [ -z "$miss_ratio" ] || [ -z "$byte_miss_ratio" ]; then
                echo "Warning: Could not extract miss ratios from output for $algo/$param!" | tee -a "$output_dir/warnings.log"
                echo "Last line: $last_line" >> "$output_dir/warnings.log"
            fi
        else
            echo "Warning: Last line does not contain 'miss ratio' for $algo/$param" | tee -a "$output_dir/warnings.log"
            echo "Last line: $last_line" >> "$output_dir/warnings.log"
        fi
    else
        echo "Error: Output file not found for $algo/$param!" | tee -a "$output_dir/warnings.log"
    fi

    # Calculate monitored stats
    if [ -f "$cpu_monitor_log" ]; then
        # Check if file exists and has content
        if [ $(wc -l < "$cpu_monitor_log") -gt 1 ]; then
            # Debug: print CPU log contents
            if [ "$DEBUG_MODE" = true ]; then
                echo "Debug: CPU log content for $algo/$param:" >> "$output_dir/debug.log"
                cat "$cpu_monitor_log" >> "$output_dir/debug.log"
                echo "End of CPU log" >> "$output_dir/debug.log"
            fi

            # Get elapsed time from the last entry in the log
            elapsed_time=$(tail -n 1 "$cpu_monitor_log" | awk '{print $1}')
            # If elapsed_time is empty, set to 0
            elapsed_time=${elapsed_time:-0}

            stats=$(tail -n +2 "$cpu_monitor_log" | awk '
                BEGIN { max=0; sum=0; count=0; sum_cumulative=0; }
                {
                    if ($2 != "" && $2 >= 0) {
                        sum += $2;
                        count++;
                        if ($2 > max) max=$2;
                        sum_cumulative += $2 * 0.2;  # 0.2 seconds sampling interval
                    }
                }
                END {
                    if (count > 0) printf "%.2f %.2f %.2f", sum/count, max, sum_cumulative;
                    else print "0 0 0";
                }
            ')
            avg_cpu=$(echo "$stats" | awk '{print $1}')
            max_cpu=$(echo "$stats" | awk '{print $2}')
            cumulative_cpu=$(echo "$stats" | awk '{print $3}')
        else
            echo "Warning: CPU monitor log for $algo/$param has insufficient data!" | tee -a "$output_dir/warnings.log"
            elapsed_time="0"
            avg_cpu="0"
            max_cpu="0"
            cumulative_cpu="0"
        fi
    else
        echo "Warning: CPU monitor log for $algo/$param not found!" | tee -a "$output_dir/warnings.log"
        elapsed_time="0"
        avg_cpu="0"
        max_cpu="0"
        cumulative_cpu="0"
    fi

    if [ -f "$memory_monitor_log" ]; then
        # Check if file exists and has content
        if [ $(wc -l < "$memory_monitor_log") -gt 1 ]; then
            # Debug: print memory log contents
            if [ "$DEBUG_MODE" = true ]; then
                echo "Debug: Memory log content for $algo/$param:" >> "$output_dir/debug.log"
                cat "$memory_monitor_log" >> "$output_dir/debug.log"
                echo "End of memory log" >> "$output_dir/debug.log"
            fi

            mem_stats=$(tail -n +2 "$memory_monitor_log" | awk '
                BEGIN { max=0; sum=0; count=0; }
                {
                    if ($2 != "" && $2 >= 0) {
                        sum += $2;
                        count++;
                        if ($2 > max) max=$2;
                    }
                }
                END {
                    if (count > 0) printf "%.0f %.0f", sum/count, max;
                    else print "0 0";
                }
            ')
            avg_memory=$(echo "$mem_stats" | awk '{print $1}')
            peak_memory=$(echo "$mem_stats" | awk '{print $2}')
        else
            echo "Warning: Memory monitor log for $algo/$param has insufficient data!" | tee -a "$output_dir/warnings.log"
            avg_memory="0"
            peak_memory="0"
        fi
    else
        echo "Warning: Memory monitor log for $algo/$param not found!" | tee -a "$output_dir/warnings.log"
        avg_memory="0"
        peak_memory="0"
    fi

    # Prepare output lines
    local perf_line="$algo $param $miss_ratio $byte_miss_ratio $throughput"
    local cpu_line="$algo $param $elapsed_time $avg_cpu $max_cpu $cumulative_cpu"
    local mem_line="$algo $param $avg_memory $peak_memory"

    # Write to files
    echo "$perf_line" >> "$output_dir/performance.txt"
    echo "$cpu_line" >> "$output_dir/CPU.txt"
    echo "$mem_line" >> "$output_dir/memory.txt"

    # Print combined results to terminal
    echo "---"
    echo "Result for $algo / $param:"
    echo "  Performance: $perf_line"
    echo "  CPU Usage:   $cpu_line"
    echo "  Memory Usage: $mem_line"
    echo "---"
}

# Function to get current system memory usage percentage
get_system_memory_usage() {
    # Get memory information from /proc/meminfo
    local mem_info=$(cat /proc/meminfo)

    # Extract total and available memory
    local total_mem=$(echo "$mem_info" | grep "MemTotal:" | awk '{print $2}')
    local available_mem=$(echo "$mem_info" | grep "MemAvailable:" | awk '{print $2}')

    # Calculate usage percentage
    local used_mem=$((total_mem - available_mem))
    local usage_percent=$(echo "scale=2; $used_mem * 100 / $total_mem" | bc)

    echo "$usage_percent"
}

# Function to wait until we have fewer than $MAX_PARALLEL jobs running
wait_for_job_slot() {
    local memory_limit="$MEMORY_LIMIT"  # Memory usage threshold percentage from command line
    local current_time=$(date +%s)  # 获取当前时间戳（秒）
    local time_since_last_start=$((current_time - last_process_start_time))

    # 如果距离上一个进程启动不足5分钟（300秒），则等待
    if [ $last_process_start_time -ne 0 ] && [ $time_since_last_start -lt 300 ]; then
        local wait_time=$((300 - time_since_last_start))
        echo "$(date): Waiting $wait_time more seconds before starting next process (5-minute spacing requirement)"
        sleep $wait_time
    fi

    while true; do
        # First check memory usage
        local current_memory_usage=$(get_system_memory_usage)

        # Check if we have fewer than MAX_PARALLEL jobs AND memory usage is below limit
        # Use bc for decimal comparison
        if [ ${#job_pids[@]} -lt $MAX_PARALLEL ] && [ $(echo "$current_memory_usage < $memory_limit" | bc -l) -eq 1 ]; then
            break
        fi

        # Check each job to see if it's still running
        for i in "${!job_pids[@]}"; do
            if ! ps -p ${job_pids[$i]} > /dev/null 2>&1; then
                # Job has completed, remove it from the array
                unset "job_pids[$i]"
            fi
        done

        # If we still have memory issues or max jobs running, wait a bit
        if [ ${#job_pids[@]} -ge $MAX_PARALLEL ] || [ $(echo "$current_memory_usage >= $memory_limit" | bc -l) -eq 1 ]; then
            if [ $(echo "$current_memory_usage >= $memory_limit" | bc -l) -eq 1 ]; then
                echo "$(date): Memory usage at ${current_memory_usage}%, waiting for it to drop below ${memory_limit}%"
            else
                echo "$(date): Active jobs: ${#job_pids[@]}/$MAX_PARALLEL, memory usage: ${current_memory_usage}%"
            fi
            sleep 2
        fi
    done
}

# Test run a single simulation in foreground if debug mode is enabled
if [ "$DEBUG_RUN_SINGLE" = true ]; then
    echo "===== DEBUG MODE: Running a single test in foreground ====="
    TEST_ALGO=${ALGO_ARRAY[0]}
    TEST_PARAM=${PARAM_ARRAY[0]}

    # Find first zst file in data directory (excluding test, MetaKV, MetaCDN, Alibaba, and TencentCBS directories)
    TEST_TRACE=$(find "$DATA_DIR" -mindepth 2 -type f -name "*.zst" | grep -v "/test/" | grep -v "/MetaKV/" | grep -v "/MetaCDN/" | grep -v "/Alibaba/" | grep -v "/TencentCBS/" | head -n 1)

    if [ -z "$TEST_TRACE" ]; then
        echo "Error: No trace files found in $DATA_DIR"
        exit 1
    fi

    echo "Using trace file: $TEST_TRACE"
    TEST_CMD="./_build/bin/cachesim \"$TEST_TRACE\" \"$TRACE_FORMAT\" \"$TEST_ALGO\" \"$TEST_PARAM\""
    echo "Running test command: $TEST_CMD"
    echo "Command output:"
    echo "-----------------------------------"
    eval "$TEST_CMD"
    echo "-----------------------------------"
    echo "Test completed. Check for errors above."
    echo "Press Enter to continue with parallel simulations or Ctrl+C to stop..."
    read -r
fi

# Main execution loop - prepare all tasks first, then schedule based on available slots
echo "Starting simulations at $(date)"

# Get all zst files (excluding test, MetaKV, MetaCDN, Alibaba, and TencentCBS directories)
zst_files=($(find "$DATA_DIR" -mindepth 2 -type f -name "*.zst" | grep -v "/test/" | grep -v "/MetaKV/" | grep -v "/MetaCDN/" | grep -v "/Alibaba/" | grep -v "/TencentCBS/" | sort))

echo "Found ${#zst_files[@]} trace files to process"

# Create an array to hold all tasks
declare -a all_tasks

# First prepare all tasks
total_tasks=0
for zst_file in "${zst_files[@]}"; do
    # Extract file and directory names
    trace_name=$(basename "$zst_file")
    trace_dir=$(dirname "$zst_file")

    # Skip if in test, MetaKV, MetaCDN, Alibaba, or TencentCBS directories
    if [[ "$trace_dir" == *"/test/"* || "$trace_dir" == *"/MetaKV/"* || "$trace_dir" == *"/MetaCDN/"* || "$trace_dir" == *"/Alibaba/"* || "$trace_dir" == *"/TencentCBS/"* ]]; then
        echo "Skipping excluded directory file: $zst_file"
        continue
    fi

    echo "Preparing tasks for trace: $zst_file"

    # Create a directory for the current trace
    trace_output_dir="$OUTPUT_DIR/$trace_name"
    mkdir -p "$trace_output_dir"

    # Initialize output files with headers
    echo "# Algorithm Parameter MissRatio ByteMissRatio Throughput(MQPS)" > "$trace_output_dir/performance.txt"
    echo "# Algorithm Parameter ElapsedTime(s) AvgCPU_Monitor(%) MaxCPU_Monitor(%) CumulativeCPU_Monitor(%*s)" > "$trace_output_dir/CPU.txt"
    echo "# Algorithm Parameter AvgMemory_Monitor(KB) PeakMemory_Monitor(KB)" > "$trace_output_dir/memory.txt"

    # Store all combinations for this trace file
    for algo in "${ALGO_ARRAY[@]}"; do
        for param in "${PARAM_ARRAY[@]}"; do
            all_tasks+=("$zst_file:$trace_output_dir:$algo:$param")
            total_tasks=$((total_tasks + 1))
        done
    done
done

echo "Total tasks to run: $total_tasks"

# Create arrays to track task completion
job_pids=()
job_tasks=()
completed_tasks=0
last_process_start_time=0  # 记录上一个进程启动的时间戳

# Function to generate a summary for completed trace files
generate_summary() {
    local completed_traces=()
    local in_progress_traces=()

    # Get current system stats
    local current_mem_usage=$(get_system_memory_usage)
    local active_jobs=${#job_pids[@]}

    echo "$(date): Generating summary - Memory: ${current_mem_usage}%, Active jobs: $active_jobs/$MAX_PARALLEL"

    # Check which trace files still have running tasks
    for task in "${job_tasks[@]}"; do
        local trace_file=$(echo "$task" | cut -d ':' -f 1)
        if [[ ! " ${in_progress_traces[@]} " =~ " $trace_file " ]]; then
            in_progress_traces+=("$trace_file")
        fi
    done

    # Check all trace files we've seen to see if any are complete
    for zst_file in "${zst_files[@]}"; do
        # Skip if file still has tasks in progress
        if [[ " ${in_progress_traces[@]} " =~ " $zst_file " ]]; then
            continue
        fi

        # Check if we've already summarized this file
        local trace_name=$(basename "$zst_file")
        local summary_flag="$OUTPUT_DIR/$trace_name/.summary_generated"

        if [ ! -f "$summary_flag" ] && [ -f "$OUTPUT_DIR/$trace_name/performance.txt" ]; then
            completed_traces+=("$zst_file")
            local trace_output_dir="$OUTPUT_DIR/$trace_name"

            echo "All simulations for $trace_name completed"
            echo "Results saved to $trace_output_dir"

            # Print summary for this trace
            echo -e "\n===== SUMMARY for $trace_name ====="
            echo "Performance metrics:"
            cat "$trace_output_dir/performance.txt"
            echo -e "\nCPU usage:"
            cat "$trace_output_dir/CPU.txt"
            echo -e "\nMemory usage:"
            cat "$trace_output_dir/memory.txt"
            echo -e "\n===== End of summary for $trace_name =====\n"

            # Mark as summarized
            touch "$summary_flag"
        fi
    done
}

# Schedule and run all tasks
for task in "${all_tasks[@]}"; do
    # Parse task info
    IFS=':' read -r zst_file trace_output_dir algo param <<< "$task"

    # Wait until we have a free slot
    wait_for_job_slot

    # Run simulation in background
    run_simulation "$zst_file" "$TRACE_FORMAT" "$algo" "$param" "$trace_output_dir" &

    # Store PID and task info
    job_pids+=($!)
    job_tasks+=("$task")

    # Track progress
    completed_tasks=$((completed_tasks + 1))
    current_mem_usage=$(get_system_memory_usage)
    echo "Scheduled task $completed_tasks of $total_tasks: $algo with param $param for $(basename "$zst_file") (Memory: ${current_mem_usage}%, Active jobs: ${#job_pids[@]}/$MAX_PARALLEL)"

    # Generate summaries for any completed trace files
    generate_summary
done

# Wait for all remaining jobs to complete
echo "Waiting for all remaining simulations to complete..."
for i in "${!job_pids[@]}"; do
    wait "${job_pids[$i]}" 2>/dev/null
    echo "Completed task: ${job_tasks[$i]}"
done

# Final summary generation
generate_summary

# Clean up summary flags
find "$OUTPUT_DIR" -name ".summary_generated" -delete

echo "All trace files processed at $(date)"
