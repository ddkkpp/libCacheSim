set -e
compute_reuse() {
  local trace="$1" file="$2"
  awk -F: 'BEGIN{in_v=0} /^# reuse virtual time:/ {in_v=1; next} /^#/ {next} in_v && NF==2 {print $1":"$2}' "$file" \
    | sort -n -t: -k1,1 \
    | awk -F: -v trace="$trace" '
      BEGIN{n=0;sum=0;total=0}
      {v=$1+0; c=$2+0; n++; vals[n]=v; cnts[n]=c; sum+=v*c; total+=c}
      END{q50=(total+1)*0.50; q90=(total+1)*0.90; q99=(total+1)*0.99; cum=0; p50=""; p90=""; p99="";
          for(k=1;k<=n;k++){cum+=cnts[k]; if(p50==""&&cum>=q50)p50=vals[k]; if(p90==""&&cum>=q90)p90=vals[k]; if(p99==""&&cum>=q99)p99=vals[k]}
          printf "recency_vtime\t%s\t%.0f\t%.6f\t%s\t%s\t%s\n", trace, total, sum/total, p50, p90, p99}'
}
compute_size() {
  local trace="$1" file="$2"
  awk -F: '!/^#/ && NF==2 {print $1":"$2}' "$file" \
    | sort -n -t: -k1,1 \
    | awk -F: -v trace="$trace" '
      BEGIN{n=0;sum=0;total=0}
      {v=$1+0; c=$2+0; n++; vals[n]=v; cnts[n]=c; sum+=v*c; total+=c}
      END{q50=(total+1)*0.50; q90=(total+1)*0.90; q99=(total+1)*0.99; cum=0; p50=""; p90=""; p99="";
          for(k=1;k<=n;k++){cum+=cnts[k]; if(p50==""&&cum>=q50)p50=vals[k]; if(p90==""&&cum>=q90)p90=vals[k]; if(p99==""&&cum>=q99)p99=vals[k]}
          printf "size_req_weighted\t%s\t%.0f\t%.6f\t%s\t%s\t%s\n", trace, total, sum/total, p50, p90, p99}'
}
compute_pop() {
  local trace="$1" file="$2"
  awk -F: '!/^#/ && NF==2 {print $1":"$2}' "$file" \
    | sort -n -t: -k1,1 \
    | awk -F: -v trace="$trace" '
      BEGIN{n=0;obj_total=0;req_total=0;sum=0;sumsq=0;one=0;maxf=0}
      {f=$1+0; c=$2+0; n++; vals[n]=f; cnts[n]=c; obj_total+=c; req_total+=f*c; sum+=f*c; sumsq+=f*f*c; if(f==1) one=c; if(f>maxf) maxf=f}
      END{mean=sum/obj_total; var=(sumsq/obj_total)-mean*mean; if(var<0)var=0; cv=(mean>0)?sqrt(var)/mean:0;
          q50=(obj_total+1)*0.50; q90=(obj_total+1)*0.90; q99=(obj_total+1)*0.99; cum=0; p50=""; p90=""; p99="";
          for(k=1;k<=n;k++){cum+=cnts[k]; if(p50==""&&cum>=q50)p50=vals[k]; if(p90==""&&cum>=q90)p90=vals[k]; if(p99==""&&cum>=q99)p99=vals[k]}
          printf "frequency_obj\t%s\t%.0f\t%.6f\t%s\t%s\t%s\t%.6f\t%.6f\t%.6f\n", trace, obj_total, mean, p50, p90, p99, one/obj_total, cv, maxf/req_total}'
}

echo -e "metric\ttrace\ttotal\tmean\tp50\tp90\tp99\tone_hit\tcv\ttop1_req_share" > tmp/trace_dist_stats_0314/summary_sorted.tsv
compute_reuse 1063 analysis/1063.oracleGeneral.zst.reuse >> tmp/trace_dist_stats_0314/summary_sorted.tsv
compute_reuse wiki analysis/wiki_2019t.oracleGeneral.zst.reuse >> tmp/trace_dist_stats_0314/summary_sorted.tsv
compute_reuse meta analysis/meta_reag.oracleGeneral.zst.reuse >> tmp/trace_dist_stats_0314/summary_sorted.tsv
compute_size 1063 analysis/1063.oracleGeneral.zst.size >> tmp/trace_dist_stats_0314/summary_sorted.tsv
compute_size wiki analysis/wiki_2019t.oracleGeneral.zst.size >> tmp/trace_dist_stats_0314/summary_sorted.tsv
compute_size meta analysis/meta_reag.oracleGeneral.zst.size >> tmp/trace_dist_stats_0314/summary_sorted.tsv
compute_pop 1063 analysis/1063.oracleGeneral.zst.popularity >> tmp/trace_dist_stats_0314/summary_sorted.tsv
compute_pop wiki analysis/wiki_2019t.oracleGeneral.zst.popularity >> tmp/trace_dist_stats_0314/summary_sorted.tsv
compute_pop meta analysis/meta_reag.oracleGeneral.zst.popularity >> tmp/trace_dist_stats_0314/summary_sorted.tsv
cat tmp/trace_dist_stats_0314/summary_sorted.tsv
