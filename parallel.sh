#!/bin/bash

result_dir="result/"
CONDA_ENV_NAME="webarena"

# get the number of tmux panes
num_panes=$(tmux list-panes | wc -l)

# calculate how many panes need to be created
let "panes_to_create = 7 - num_panes"

# array of tmux commands to create each pane
tmux_commands=(
    'tmux split-window -h'
    'tmux split-window -v'
    'tmux select-pane -t 0; tmux split-window -v'
    'tmux split-window -v'
    'tmux select-pane -t 3; tmux split-window -v'
    'tmux select-pane -t 5; tmux split-window -v'
)

# create panes up to 7
for ((i=0; i<$panes_to_create; i++)); do
    eval ${tmux_commands[$i]}
done

#!/bin/bash

# Function to run a job
# run_job() {
#     tmux select-pane -t $1
#     tmux send-keys "conda activate ${CONDA_ENV_NAME}; until python -m Pipeline.pipelines.webarena_test --start_idx $2 --end_idx $3 --result_dir ${result_dir} --sample 13; do echo 'crashed' >&2; sleep 1; done" C-m
#     sleep 3
# }

run_job() {
    tmux select-pane -t $1
    tmux send-keys "conda activate ${CONDA_ENV_NAME}; until python -m Pipeline.pipelines.webarena_test --start_idx $2 --end_idx $3 --result_dir ${result_dir} --sample 13; do echo 'crashed' >&2; sleep 1; done" C-m
    sleep 3
}

run_batch() {
    args=("$@") # save all arguments in an array
    num_jobs=${#args[@]} # get number of arguments

    for ((i=1; i<$num_jobs; i++)); do
        run_job $i ${args[i-1]} ${args[i]}
    done

    # Wait for all jobs to finish
    while tmux list-panes -F "#{pane_pid} #{pane_current_command}" | grep -q python; do
        sleep 100  # wait for 10 seconds before checking again
    done
}

# run_batch 0 136 271 406 542 677 812
run_batch 0 271 542 812
# python get_result.py ${result_dir}
