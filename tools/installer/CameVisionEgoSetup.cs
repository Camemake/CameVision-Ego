using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Threading;
using System.Windows.Forms;

namespace Camemake
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new SetupForm());
        }
    }

    sealed class SetupForm : Form
    {
        static readonly Color Came = Color.FromArgb(26, 111, 124);
        static readonly Color Pink = Color.FromArgb(232, 75, 138);
        static readonly Color PinkHot = Color.FromArgb(214, 61, 121);
        static readonly Color Bg = Color.FromArgb(244, 239, 232);
        static readonly Color Ink = Color.FromArgb(34, 34, 34);
        static readonly Color Muted = Color.FromArgb(92, 92, 92);
        static readonly Color Line = Color.FromArgb(228, 221, 212);
        static readonly Color Card = Color.White;

        readonly string _root;
        readonly Label[] _st;
        readonly TextBox _log;
        readonly Button _btn;
        readonly string[] _ids = { "python", "host", "files", "usb", "images", "finish" };
        readonly string[] _names =
        {
            "Python runtime",
            "ADB and flash tool",
            "Package files",
            "USB access",
            "Board images",
            "Finish"
        };
        bool _busy;
        bool _done;

        public SetupForm()
        {
            _root = FindRoot();
            Text = "CameVision Ego";
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            ClientSize = new Size(520, 640);
            BackColor = Bg;
            Font = new Font("Segoe UI", 10f);
            ForeColor = Ink;
            Icon = SystemIcons.Application;

            var header = new Panel
            {
                Dock = DockStyle.Top,
                Height = 78,
                BackColor = Card,
                Padding = new Padding(20, 0, 20, 0)
            };
            header.Paint += (s, e) =>
            {
                using (var p = new Pen(Line))
                    e.Graphics.DrawLine(p, 0, header.Height - 1, header.Width, header.Height - 1);
            };

            var logo = LoadLogo();
            if (logo != null)
            {
                var pic = new PictureBox
                {
                    Image = logo,
                    SizeMode = PictureBoxSizeMode.Zoom,
                    Size = new Size(120, 36),
                    Location = new Point(20, 21),
                    BackColor = Card
                };
                header.Controls.Add(pic);
            }

            var title = new Label
            {
                Text = "CameVision Ego",
                Font = new Font("Segoe UI", 16f, FontStyle.Bold),
                ForeColor = Ink,
                BackColor = Card,
                AutoSize = true,
                Location = new Point(150, 16)
            };
            var sub = new Label
            {
                Text = "Camemake installer",
                Font = new Font("Segoe UI", 11f),
                ForeColor = Came,
                BackColor = Card,
                AutoSize = true,
                Location = new Point(150, 44)
            };
            header.Controls.Add(title);
            header.Controls.Add(sub);
            Controls.Add(header);

            var lead = new Label
            {
                Text = "Installs every pack that ships in this folder. Same window on an empty PC.",
                Location = new Point(28, 96),
                Size = new Size(464, 40),
                ForeColor = Muted,
                BackColor = Bg
            };
            Controls.Add(lead);

            var card = new Panel
            {
                Location = new Point(28, 140),
                Size = new Size(464, 196),
                BackColor = Card
            };
            card.Paint += (s, e) =>
            {
                using (var p = new Pen(Line))
                    e.Graphics.DrawRectangle(p, 0, 0, card.Width - 1, card.Height - 1);
            };
            _st = new Label[_names.Length];
            for (int i = 0; i < _names.Length; i++)
            {
                var name = new Label
                {
                    Text = _names[i],
                    Location = new Point(16, 10 + i * 30),
                    Size = new Size(260, 24),
                    BackColor = Card,
                    ForeColor = Ink
                };
                var st = new Label
                {
                    Text = "Waiting",
                    Location = new Point(300, 10 + i * 30),
                    Size = new Size(148, 24),
                    TextAlign = ContentAlignment.MiddleRight,
                    BackColor = Card,
                    ForeColor = Muted
                };
                _st[i] = st;
                card.Controls.Add(name);
                card.Controls.Add(st);
            }
            Controls.Add(card);

            _log = new TextBox
            {
                Location = new Point(28, 350),
                Size = new Size(464, 180),
                Multiline = true,
                ReadOnly = true,
                ScrollBars = ScrollBars.Vertical,
                BackColor = Card,
                ForeColor = Ink,
                BorderStyle = BorderStyle.FixedSingle,
                Font = new Font("Consolas", 9f),
                Text = "Ready." + Environment.NewLine
            };
            Controls.Add(_log);

            _btn = new Button
            {
                Text = "Install",
                Location = new Point(28, 548),
                Size = new Size(140, 40),
                FlatStyle = FlatStyle.Flat,
                BackColor = Pink,
                ForeColor = Color.White,
                Font = new Font("Segoe UI", 11f, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            _btn.FlatAppearance.BorderSize = 0;
            _btn.FlatAppearance.MouseOverBackColor = PinkHot;
            _btn.Click += OnClick;
            Controls.Add(_btn);

            var foot = new Label
            {
                Text = "© Camemake  ·  CV-EGO01-OS",
                Location = new Point(180, 556),
                Size = new Size(312, 28),
                ForeColor = Muted,
                BackColor = Bg,
                TextAlign = ContentAlignment.MiddleRight
            };
            Controls.Add(foot);
        }

        Image LoadLogo()
        {
            string[] cands =
            {
                Path.Combine(_root, "tools", "camemake-logo.png"),
                Path.Combine(_root, "docs", "assets", "camemake-logo.png")
            };
            foreach (var p in cands)
            {
                if (!File.Exists(p)) continue;
                try { return Image.FromFile(p); }
                catch { }
            }
            return null;
        }

        static string FindRoot()
        {
            var dir = Path.GetDirectoryName(Application.ExecutablePath) ?? Environment.CurrentDirectory;
            if (File.Exists(Path.Combine(dir, "tools", "cv_ego_setup.py")))
                return dir;
            throw new InvalidOperationException(
                "CameVision-Ego.exe must sit in the unzipped package folder (next to tools/). " +
                "Do not copy the exe out, and do not run the one from another tree.");
        }

        string Python()
        {
            var pyw = Path.Combine(_root, "host", "python", "pythonw.exe");
            var py = Path.Combine(_root, "host", "python", "python.exe");
            if (File.Exists(py)) return py;
            if (File.Exists(pyw)) return pyw;
            return "";
        }

        void Log(string line)
        {
            if (InvokeRequired)
            {
                BeginInvoke(new Action<string>(Log), line);
                return;
            }
            _log.AppendText(line + Environment.NewLine);
        }

        void SetStatus(int i, string text, Color color)
        {
            if (InvokeRequired)
            {
                BeginInvoke(new Action<int, string, Color>(SetStatus), i, text, color);
                return;
            }
            _st[i].Text = text;
            _st[i].ForeColor = color;
        }

        void OnClick(object sender, EventArgs e)
        {
            if (_busy) return;
            if (_done)
            {
                LaunchTool();
                return;
            }
            _busy = true;
            _btn.Enabled = false;
            var t = new Thread(Install) { IsBackground = true };
            t.Start();
        }

        void Install()
        {
            var py = Python();
            if (py.Length == 0)
            {
                Log("Python runtime missing from this package.");
                Done(false);
                return;
            }
            var setup = Path.Combine(_root, "tools", "cv_ego_setup.py");
            for (int i = 0; i < _ids.Length; i++)
            {
                SetStatus(i, "Installing", Came);
                Log("=== " + _names[i] + " ===");
                int code = RunPython(py, setup, "--pack " + _ids[i]);
                if (code != 0)
                {
                    SetStatus(i, "Failed", Color.FromArgb(192, 57, 43));
                    Done(false);
                    return;
                }
                SetStatus(i, "Installed", Came);
                Log("ok");
            }
            Log("Opening the offline tool…");
            LaunchTool();
            Done(true);
        }

        int RunPython(string py, string script, string args)
        {
            var psi = new ProcessStartInfo
            {
                FileName = py,
                Arguments = "\"" + script + "\" " + args,
                WorkingDirectory = _root,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };
            psi.EnvironmentVariables["CAMEVISION_EGO_ROOT"] = _root;
            psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";
            try
            {
                using (var p = Process.Start(psi))
                {
                    if (p == null) return 1;
                    p.OutputDataReceived += (s, e) => { if (!string.IsNullOrEmpty(e.Data)) Log(e.Data); };
                    p.ErrorDataReceived += (s, e) => { if (!string.IsNullOrEmpty(e.Data)) Log(e.Data); };
                    p.BeginOutputReadLine();
                    p.BeginErrorReadLine();
                    p.WaitForExit();
                    return p.ExitCode;
                }
            }
            catch (Exception ex)
            {
                Log(ex.Message);
                return 1;
            }
        }

        void LaunchTool()
        {
            var py = Python();
            var studio = Path.Combine(_root, "tools", "cv_ego_studio.py");
            if (py.Length == 0 || !File.Exists(studio)) return;
            var psi = new ProcessStartInfo
            {
                FileName = py,
                Arguments = "\"" + studio + "\"",
                WorkingDirectory = _root,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            psi.EnvironmentVariables["CAMEVISION_EGO_ROOT"] = _root;
            try { Process.Start(psi); }
            catch (Exception ex) { Log(ex.Message); }
        }

        void Done(bool ok)
        {
            if (InvokeRequired)
            {
                BeginInvoke(new Action<bool>(Done), ok);
                return;
            }
            _busy = false;
            _done = ok;
            _btn.Enabled = true;
            if (ok) _btn.Text = "Open";
        }
    }
}
