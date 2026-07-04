#include <windows.h>
#include <wchar.h>
#include <stdio.h>

// Callback function type definition
typedef void (__stdcall *ProjectFoundCallback)(const wchar_t* path, const wchar_t* type);

// Helper to check if a directory should be skipped
int should_skip_dir(const wchar_t* name) {
    return (wcscmp(name, L".") == 0 || 
            wcscmp(name, L"..") == 0 || 
            wcscmp(name, L".git") == 0 || 
            wcscmp(name, L"node_modules") == 0 || 
            wcscmp(name, L"venv") == 0 || 
            wcscmp(name, L".venv") == 0 || 
            wcscmp(name, L"__pycache__") == 0 || 
            wcscmp(name, L"dist") == 0 || 
            wcscmp(name, L"build") == 0 || 
            wcscmp(name, L"target") == 0 || 
            wcscmp(name, L"bin") == 0 || 
            wcscmp(name, L"obj") == 0);
}

// Recursive function to search for projects
void search_directory(const wchar_t* current_path, int depth, int max_depth, ProjectFoundCallback callback) {
    if (depth > max_depth) return;

    wchar_t search_pattern[32768];
    swprintf(search_pattern, 32768, L"%s\\*", current_path);

    WIN32_FIND_DATAW find_data;
    HANDLE h_find = FindFirstFileW(search_pattern, &find_data);

    if (h_find == INVALID_HANDLE_VALUE) return;

    int is_project = 0;
    wchar_t project_type[64] = L"";

    // First Pass: Check if the current directory is a project root
    do {
        if (!(find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
            // Check for node.js project
            if (wcscmp(find_data.cFileName, L"package.json") == 0) {
                is_project = 1;
                wcscpy(project_type, L"Node.js");
                break;
            }
            // Check for python project requirements
            else if (wcscmp(find_data.cFileName, L"requirements.txt") == 0 || 
                     wcscmp(find_data.cFileName, L"pyproject.toml") == 0 ||
                     wcscmp(find_data.cFileName, L"Pipfile") == 0) {
                is_project = 1;
                wcscpy(project_type, L"Python");
                break;
            }
            // Check for Rust project
            else if (wcscmp(find_data.cFileName, L"Cargo.toml") == 0) {
                is_project = 1;
                wcscpy(project_type, L"Rust");
                break;
            }
            // Check for Go project
            else if (wcscmp(find_data.cFileName, L"go.mod") == 0) {
                is_project = 1;
                wcscpy(project_type, L"Go");
                break;
            }
            // Check for C/C++ project
            else if (wcscmp(find_data.cFileName, L"CMakeLists.txt") == 0 ||
                     wcscmp(find_data.cFileName, L"Makefile") == 0) {
                is_project = 1;
                wcscpy(project_type, L"C/C++");
                break;
            }
            // Check for Java/Kotlin project
            else if (wcscmp(find_data.cFileName, L"pom.xml") == 0 ||
                     wcscmp(find_data.cFileName, L"build.gradle") == 0 ||
                     wcscmp(find_data.cFileName, L"build.gradle.kts") == 0) {
                is_project = 1;
                wcscpy(project_type, L"Java/Kotlin");
                break;
            }
            // Check for C#/.NET project
            else if (wcsstr(find_data.cFileName, L".csproj") != NULL ||
                     wcsstr(find_data.cFileName, L".sln") != NULL) {
                is_project = 1;
                wcscpy(project_type, L"C#/.NET");
                break;
            }
            // Check for PHP project
            else if (wcscmp(find_data.cFileName, L"composer.json") == 0) {
                is_project = 1;
                wcscpy(project_type, L"PHP");
                break;
            }
            // Check for Ruby project
            else if (wcscmp(find_data.cFileName, L"Gemfile") == 0) {
                is_project = 1;
                wcscpy(project_type, L"Ruby");
                break;
            }
            // Check for static web project
            else if (wcscmp(find_data.cFileName, L"index.html") == 0) {
                is_project = 1;
                wcscpy(project_type, L"HTML/CSS");
                // Don't break immediately in case a package.json exists (which is preferred)
            }
        }
    } while (FindNextFileW(h_find, &find_data));

    // If we found a project in this folder, report it and STOP recursing deeper
    if (is_project) {
        callback(current_path, project_type);
        FindClose(h_find);
        return;
    }

    // Second Pass: Recurse into subdirectories if we haven't found a project here
    FindClose(h_find);
    h_find = FindFirstFileW(search_pattern, &find_data);
    if (h_find == INVALID_HANDLE_VALUE) return;

    do {
        if (find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            if (!should_skip_dir(find_data.cFileName)) {
                wchar_t next_path[32768];
                swprintf(next_path, 32768, L"%s\\%s", current_path, find_data.cFileName);
                search_directory(next_path, depth + 1, max_depth, callback);
            }
        }
    } while (FindNextFileW(h_find, &find_data));

    FindClose(h_find);
}

// Exported function for Python ctypes to invoke
__declspec(dllexport) void scan_projects(const wchar_t* root_dir, int max_depth, ProjectFoundCallback callback) {
    if (!root_dir || !callback) return;
    search_directory(root_dir, 0, max_depth, callback);
}
