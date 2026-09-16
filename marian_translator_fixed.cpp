#include "marian_translator.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <unordered_set>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace {

const std::string SPIECE = "\xE2\x96\x81";

size_t utf8_len(const std::string& s, size_t i) {
    const unsigned char c = static_cast<unsigned char>(s[i]);
    if (c < 0x80) return 1;
    if ((c >> 5) == 0x06) return 2;
    if ((c >> 4) == 0x0E) return 3;
    if ((c >> 3) == 0x1E) return 4;
    return 1;
}

std::string to_spiece(const std::string& text) {
    std::string out;
    bool at_word_start = true;
    size_t i = 0;
    while (i < text.size() && std::isspace(static_cast<unsigned char>(text[i]))) ++i;
    for (; i < text.size(); ++i) {
        if (std::isspace(static_cast<unsigned char>(text[i]))) {
            at_word_start = true;
            continue;
        }
        if (at_word_start) {
            out += SPIECE;
            at_word_start = false;
        }
        out += text[i];
    }
    return out;
}

}  // namespace

MarianTranslator::MarianTranslator(const std::string& en2lun_dir, const std::string& lun2en_dir)
    : env_(ORT_LOGGING_LEVEL_WARNING, "MarianTranslator") {
    load_direction(en2lun_dir, en2lun_, "marian en2lun");
    load_direction(lun2en_dir, lun2en_, "marian lun2en");
}

void MarianTranslator::load_direction(const std::string& dir, Direction& d, const char* label) {
    try {
        Ort::SessionOptions opts;
        opts.SetIntraOpNumThreads(2);
        opts.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        d.encoder = std::make_unique<Ort::Session>(env_, (dir + "/encoder_model.onnx").c_str(), opts);
        d.decoder = std::make_unique<Ort::Session>(env_, (dir + "/decoder_model.onnx").c_str(), opts);
        load_unigram(dir + "/unigram_source.json", d);
        d.loaded = true;
        std::cout << "  Loaded " << label << ": " << d.piece_scores.size() << " pieces, "
                  << d.vocab.size() << " vocab, start=" << d.decoder_start_id << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "  [WARN] " << label << " unavailable: " << e.what() << std::endl;
        d.loaded = false;
    }
}

void MarianTranslator::load_unigram(const std::string& path, Direction& d) {
    std::ifstream f(path);
    if (!f.is_open()) throw std::runtime_error("cannot open " + path);
    json data = json::parse(f);
    for (const auto& entry : data["pieces"]) {
        std::string piece = entry[0].get<std::string>();
        float score = entry[1].get<float>();
        d.max_piece_bytes = std::max(d.max_piece_bytes, piece.size());
        d.piece_scores.emplace(std::move(piece), score);
    }
    for (auto it = data["vocab"].begin(); it != data["vocab"].end(); ++it) {
        int64_t id = it.value().get<int64_t>();
        d.vocab.emplace(it.key(), id);
        d.inv_vocab.emplace(id, it.key());
    }
    d.unk_id = data.value("unk_id", 1);
    d.eos_id = data.value("eos_id", 0);
    d.pad_id = data.value("pad_id", 64109);
    d.decoder_start_id = data.value("decoder_start_token_id", d.pad_id);
}

std::vector<int64_t> MarianTranslator::encode(const Direction& d, const std::string& text) const {
    const std::string norm = to_spiece(text);
    const size_t n = norm.size();
    if (n == 0) return {d.eos_id};

    constexpr float kNegInf = -std::numeric_limits<float>::infinity();
    const float unk_penalty = -20.0f;
    std::vector<float> best(n + 1, kNegInf);
    std::vector<size_t> prev(n + 1, 0);
    std::vector<bool> prev_unk(n + 1, false);
    best[0] = 0.0f;

    for (size_t i = 0; i < n; ++i) {
        if (best[i] == kNegInf) continue;
        const size_t limit = std::min(n, i + std::max<size_t>(d.max_piece_bytes, 1));
        bool matched = false;
        for (size_t j = i + 1; j <= limit; ++j) {
            if (j < n) {
                const unsigned char c = static_cast<unsigned char>(norm[j]);
                if ((c & 0xC0) == 0x80) continue;
            }
            auto it = d.piece_scores.find(norm.substr(i, j - i));
            if (it == d.piece_scores.end()) continue;
            matched = true;
            const float score = best[i] + it->second;
            if (score > best[j]) {
                best[j] = score;
                prev[j] = i;
                prev_unk[j] = false;
            }
        }
        const size_t step = utf8_len(norm, i);
        const size_t j = std::min(i + step, n);
        const float score = best[i] + unk_penalty;
        if (!matched || score > best[j]) {
            if (score > best[j]) {
                best[j] = score;
                prev[j] = i;
                prev_unk[j] = true;
            }
        }
    }

    std::vector<int64_t> ids;
    std::vector<std::pair<size_t, bool>> spans;
    for (size_t i = n; i > 0;) {
        spans.emplace_back(i, prev_unk[i]);
        i = prev[i];
    }
    std::reverse(spans.begin(), spans.end());
    size_t start = 0;
    for (const auto& [end, is_unk] : spans) {
        const std::string piece = norm.substr(start, end - start);
        auto it = d.vocab.find(piece);
        ids.push_back((is_unk || it == d.vocab.end()) ? d.unk_id : it->second);
        start = end;
    }
    ids.push_back(d.eos_id);
    if (ids.size() > static_cast<size_t>(max_length_)) {
        ids.resize(max_length_);
        ids.back() = d.eos_id;
    }
    return ids;
}

std::string MarianTranslator::decode(const Direction& d, const std::vector<int64_t>& ids) const {
    std::string text;
    for (int64_t id : ids) {
        if (id == d.eos_id || id == d.pad_id || id == d.unk_id) continue;
        auto it = d.inv_vocab.find(id);
        if (it == d.inv_vocab.end()) continue;
        const std::string& piece = it->second;
        if (piece.size() >= SPIECE.size() && piece.compare(0, SPIECE.size(), SPIECE) == 0) {
            if (!text.empty()) text += ' ';
            text += piece.substr(SPIECE.size());
        } else {
            text += piece;
        }
    }
    return text;
}

std::string MarianTranslator::generate(const Direction& d, const std::string& text) const {
    const std::vector<int64_t> input_ids = encode(d, text);
    const std::vector<int64_t> attention_mask(input_ids.size(), 1);

    auto mem = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
    const std::array<int64_t, 2> in_shape{1, static_cast<int64_t>(input_ids.size())};

    auto ids_tensor = Ort::Value::CreateTensor<int64_t>(
        mem, const_cast<int64_t*>(input_ids.data()), input_ids.size(), in_shape.data(), in_shape.size());
    auto mask_tensor = Ort::Value::CreateTensor<int64_t>(
        mem, const_cast<int64_t*>(attention_mask.data()), attention_mask.size(), in_shape.data(), in_shape.size());

    const char* enc_in[] = {"input_ids", "attention_mask"};
    const char* enc_out[] = {"last_hidden_state"};
    std::array<Ort::Value, 2> enc_inputs{std::move(ids_tensor), std::move(mask_tensor)};
    auto enc_result = d.encoder->Run(Ort::RunOptions{nullptr}, enc_in, enc_inputs.data(), 2, enc_out, 1);

    const float* hidden = enc_result[0].GetTensorData<float>();
    auto hidden_shape = enc_result[0].GetTensorTypeAndShapeInfo().GetShape();
    const size_t hidden_count = enc_result[0].GetTensorTypeAndShapeInfo().GetElementCount();
    std::vector<float> hidden_buf(hidden, hidden + hidden_count);

    std::vector<int64_t> generated{d.decoder_start_id};

    // Hard output length limit: max 2x input length or 64 tokens, whichever is smaller
    const int hard_max = std::min(64, static_cast<int>(input_ids.size()) * 2 + 10);

    for (int step = 0; step < hard_max; ++step) {
        const std::array<int64_t, 2> dec_shape{1, static_cast<int64_t>(generated.size())};

        auto dec_ids = Ort::Value::CreateTensor<int64_t>(
            mem, generated.data(), generated.size(), dec_shape.data(), dec_shape.size());
        auto enc_hidden = Ort::Value::CreateTensor<float>(
            mem, hidden_buf.data(), hidden_buf.size(), hidden_shape.data(), hidden_shape.size());
        auto enc_mask = Ort::Value::CreateTensor<int64_t>(
            mem, const_cast<int64_t*>(attention_mask.data()), attention_mask.size(),
            in_shape.data(), in_shape.size());

        const char* dec_in[] = {"input_ids", "encoder_hidden_states", "encoder_attention_mask"};
        const char* dec_out[] = {"logits"};
        std::array<Ort::Value, 3> dec_inputs{std::move(dec_ids), std::move(enc_hidden), std::move(enc_mask)};
        auto dec_result = d.decoder->Run(Ort::RunOptions{nullptr}, dec_in, dec_inputs.data(), 3, dec_out, 1);

        const float* logits = dec_result[0].GetTensorData<float>();
        auto shape = dec_result[0].GetTensorTypeAndShapeInfo().GetShape();
        const int64_t seq_len = shape[1];
        const int64_t vocab_size = shape[2];
        const float* last = logits + (seq_len - 1) * vocab_size;

        // Apply repetition penalty (1.5) to all previously generated tokens
        std::vector<float> scores(last, last + vocab_size);
        const float rep_penalty = 1.5f;
        for (int64_t id : generated) {
            if (id >= 0 && id < vocab_size) {
                if (scores[id] > 0) scores[id] /= rep_penalty;
                else                scores[id] *= rep_penalty;
            }
        }

        // No-repeat bigram blocking
        if (generated.size() >= 2) {
            int64_t g1 = generated[generated.size() - 1];
            for (size_t k = 1; k < generated.size(); ++k) {
                if (generated[k - 1] == g1) {
                    int64_t blocked = generated[k];
                    if (blocked >= 0 && blocked < vocab_size)
                        scores[blocked] -= 10.0f;  // strongly discourage, not hard block
                }
            }
        }

        // No-repeat trigram blocking: hard block
        if (generated.size() >= 3) {
            int64_t g1 = generated[generated.size() - 2];
            int64_t g2 = generated[generated.size() - 1];
            for (size_t k = 2; k < generated.size(); ++k) {
                if (generated[k - 2] == g1 && generated[k - 1] == g2) {
                    int64_t blocked = generated[k];
                    if (blocked >= 0 && blocked < vocab_size)
                        scores[blocked] = -std::numeric_limits<float>::infinity();
                }
            }
        }

        int64_t best_id = 0;
        float best_score = -std::numeric_limits<float>::infinity();
        for (int64_t v = 0; v < vocab_size; ++v) {
            if (scores[v] > best_score) {
                best_score = scores[v];
                best_id = v;
            }
        }

        if (best_id == d.eos_id) break;
        generated.push_back(best_id);
    }

    return decode(d, std::vector<int64_t>(generated.begin() + 1, generated.end()));
}

bool MarianTranslator::available(bool en_to_lun) const {
    return (en_to_lun ? en2lun_ : lun2en_).loaded;
}

std::string MarianTranslator::translate(const std::string& text, bool en_to_lun) const {
    const Direction& d = en_to_lun ? en2lun_ : lun2en_;
    if (!d.loaded) return "";
    try {
        return generate(d, text);
    } catch (const std::exception& e) {
        std::cerr << "Marian translation error: " << e.what() << std::endl;
        return "";
    }
}
