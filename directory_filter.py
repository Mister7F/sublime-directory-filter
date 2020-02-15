import os
import sublime, sublime_plugin

MIN_UPDATE_PERIOD = 200


class DirectoryFilterCommand(sublime_plugin.TextCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False

    def _fdfind_clear(self, paths):
        previous_dir = ''
        ret = []
        for path in paths:
            if previous_dir in path and previous_dir or './' in path[1:]:
                continue
            ret.append(path)
            previous_dir = path
        return ret

    def _update_sidebar(self):
        if not self.search:
            self.running = False
            return

        search = self.search
        self.search = None

        # paths = os.popen('find "$(pwd -P)" -maxdepth 5 -regextype posix-extended -iregex ".*(%s).*" -readable -prune 2>/dev/null' % search).read()
        paths = os.popen("timeout 0.8s fdfind -a -i -p -c never --max-depth 10 -t d -- '%s[^/]*$' '%s' | head -100" % (search, self.current_base)).read()
        paths = paths.strip().split('\n')

        paths = self._fdfind_clear(paths)
        sublime.active_window().status_message('Found %i items' % len(paths))

        project_settings = {}
        for path in paths:
            parent_dir = path.rsplit('/', 1)[0]
            if parent_dir not in project_settings:
                project_settings[parent_dir] = {
                    'path': parent_dir,
                    'folder_include_patterns': [],
                    # ni hidden directory
                    'file_include_patterns': [],
                    'folder_exclude_patterns': [".*"],
                    'follow_symlinks': False
                }

            project_settings[parent_dir]['folder_include_patterns'].append(path + '*')
            project_settings[parent_dir]['file_include_patterns'].append(path + '*')

        sublime.active_window().set_project_data({
            'folders': list(project_settings.values()),
            'expanded_folders': paths,
            'base_dir_backup': self.current_base,
            'search_text': search,
        })

        sublime.set_timeout_async(self._update_sidebar, MIN_UPDATE_PERIOD)

    def run(self, edit):
        def on_change(text):
            self.view.settings().set('directory_filter_current_search', text)
            self.search = text.replace('"', '').replace("'", '').strip()

            if len(text) < 3:
                sublime.active_window().set_project_data({
                    'folders': [{
                        'path': self.current_base,
                        'folder_exclude_patterns': [".*"],
                        'follow_symlinks': False,
                    }],
                    'base_dir_backup': self.current_base,
                    'search_text': text,
                })
                sublime.active_window().status_message('Working directory: %s' % self.current_base)

            elif not self.running:
                self.running = True
                sublime.set_timeout_async(self._update_sidebar)

        project_data = sublime.active_window().project_data() or {}

        self.current_base = project_data.get('base_dir_backup')
        if not self.current_base:
            self.current_base = project_data.get('folders', [{}])[0].get('path')

        text = project_data.get('search_text', '')
        sublime.active_window().show_input_panel('Directory filter', text, None, on_change, None)
