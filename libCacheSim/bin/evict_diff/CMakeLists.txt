add_executable(evict_diff main.c)
target_include_directories(evict_diff PRIVATE ${libCacheSim_include_dir} ${GLib_INCLUDE_DIRS} ../)
target_link_libraries(evict_diff ${PROJECT_NAME})
